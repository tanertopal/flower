# Copyright 2020 Adap GmbH. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
"""Flower server."""


import concurrent.futures
import timeit
from logging import DEBUG, INFO
from typing import List, Optional, Tuple

from flower.client_manager import ClientManager
from flower.client_proxy import ClientProxy
from flower.history import History
from flower.logger import log
from flower.strategy import DefaultStrategy, Strategy
from flower.strategy.parameter import parameters_to_weights
from flower.typing import EvaluateIns, EvaluateRes, FitIns, FitRes, Weights


class Server:
    """Flower server."""

    def __init__(
        self, client_manager: ClientManager, strategy: Optional[Strategy] = None
    ) -> None:
        self._client_manager: ClientManager = client_manager
        self.weights: Weights = []
        self.strategy: Strategy = strategy if strategy is not None else DefaultStrategy()

    def client_manager(self) -> ClientManager:
        """Return ClientManager."""
        return self._client_manager

    def fit(self, num_rounds: int) -> History:
        """Run federated averaging for a number of rounds."""
        history = History()
        # Initialize weights by asking one client to return theirs
        self.weights = self._get_initial_weights()
        res = self.strategy.evaluate(weights=self.weights)
        if res is not None:
            log(
                INFO, "initial weights (loss/accuracy): %s, %s", res[0], res[1],
            )
            history.add_loss_centralized(rnd=0, loss=res[0])
            history.add_accuracy_centralized(rnd=0, acc=res[1])

        # Run federated learning for num_rounds
        log(INFO, "[TIME] FL starting")
        start_time = timeit.default_timer()

        for current_round in range(1, num_rounds + 1):
            # Train model and replace previous global model
            weights_prime = self.fit_round(rnd=current_round)
            if weights_prime is not None:
                self.weights = weights_prime

            # Evaluate model using strategy implementation
            loss, acc = None, None
            res = self.strategy.evaluate(weights=self.weights)
            if res is not None:
                loss, acc = res
                log(
                    INFO,
                    "progress (round/loss/accuracy): %s, %s, %s",
                    current_round,
                    loss,
                    acc,
                )
                history.add_loss_centralized(rnd=current_round, loss=loss)
                history.add_accuracy_centralized(rnd=current_round, acc=acc)

            # Evaluate model on a sample of available clients
            loss_avg = self.evaluate(rnd=current_round)
            if loss_avg is not None:
                history.add_loss_distributed(rnd=current_round, loss=loss_avg)
                loss, acc = loss_avg, None

            # Conclude round
            should_continue = self.strategy.on_conclude_round(current_round, loss, acc)
            if not should_continue:
                break

        end_time = timeit.default_timer()
        elapsed = end_time - start_time
        log(INFO, "[TIME] FL finished in %s", elapsed)
        return history

    def evaluate(self, rnd: int) -> Optional[float]:
        """Validate current global model on a number of clients."""
        # Get clients and their respective instructions from strategy
        client_instructions = self.strategy.on_configure_evaluate(
            rnd=rnd, weights=self.weights, client_manager=self._client_manager
        )
        if not client_instructions:
            return None

        # Evaluate current global weights on those clients
        results, failures = evaluate_clients(client_instructions)
        log(
            DEBUG,
            "evaluate received %s results and %s failures",
            len(results),
            len(failures),
        )
        # Aggregate the evaluation results
        return self.strategy.on_aggregate_evaluate(rnd, results, failures)

    def fit_round(self, rnd: int) -> Optional[Weights]:
        """Perform a single round of federated averaging."""
        # Get clients and their respective instructions from strategy
        client_instructions = self.strategy.on_configure_fit(
            rnd=rnd, weights=self.weights, client_manager=self._client_manager
        )
        if not client_instructions:
            return None

        # Collect training results from all clients participating in this round
        results, failures = fit_clients(client_instructions)
        log(
            DEBUG,
            "fit_round received %s results and %s failures",
            len(results),
            len(failures),
        )

        # Aggregate training results
        return self.strategy.on_aggregate_fit(rnd, results, failures)

    def _get_initial_weights(self) -> Weights:
        """Get initial weights from one of the available clients."""
        random_client = self._client_manager.sample(1)[0]
        parameters_res = random_client.get_parameters()
        return parameters_to_weights(parameters_res.parameters)


def fit_clients(
    client_instructions: List[Tuple[ClientProxy, FitIns]]
) -> Tuple[List[Tuple[ClientProxy, FitRes]], List[BaseException]]:
    """Refine weights concurrently on all selected clients."""
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(fit_client, c, ins) for c, ins in client_instructions
        ]
        concurrent.futures.wait(futures)
    # Gather results
    results: List[Tuple[ClientProxy, FitRes]] = []
    failures: List[BaseException] = []
    for future in futures:
        failure = future.exception()
        if failure is not None:
            failures.append(failure)
        else:
            # Potential success case
            result = future.result()
            if len(result[1][0].tensors) > 0:
                results.append(result)
            else:
                failures.append(Exception("Empty client update"))
    return results, failures


def fit_client(client: ClientProxy, ins: FitIns) -> Tuple[ClientProxy, FitRes]:
    """Refine weights on a single client."""
    fit_res = client.fit(ins)
    return client, fit_res


def evaluate_clients(
    client_instructions: List[Tuple[ClientProxy, FitIns]]
) -> Tuple[List[Tuple[ClientProxy, EvaluateRes]], List[BaseException]]:
    """Evaluate weights concurrently on all selected clients."""
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(evaluate_client, c, ins) for c, ins in client_instructions
        ]
        concurrent.futures.wait(futures)
    # Gather results
    results: List[Tuple[ClientProxy, EvaluateRes]] = []
    failures: List[BaseException] = []
    for future in futures:
        failure = future.exception()
        if failure is not None:
            failures.append(failure)
        else:
            # Success case
            results.append(future.result())
    return results, failures


def evaluate_client(
    client: ClientProxy, ins: EvaluateIns
) -> Tuple[ClientProxy, EvaluateRes]:
    """Evaluate weights on a single client."""
    evaluate_res = client.evaluate(ins)
    return client, evaluate_res

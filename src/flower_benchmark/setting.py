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
"""Provides a variaty of benchmark settings base classes."""

from dataclasses import dataclass
from typing import List


@dataclass
class ServerSetting:
    """Settings for the server."""

    rounds: int
    min_num_clients: int
    sample_fraction: float
    min_sample_size: int
    training_round_timeout: int
    lr_initial: float
    dry_run: bool


@dataclass
class ClientSetting:
    """Settings for the client."""

    # Individual per client
    cid: str
    partition: int
    delay_factor: float

    # Same across all clients
    iid_fraction: float
    num_clients: int
    dry_run: bool


@dataclass
class Setting:
    """One specific training setting."""

    server: ServerSetting
    clients: List[ClientSetting]

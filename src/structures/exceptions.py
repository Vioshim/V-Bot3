# Copyright 2021 Vioshim
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from discord.ext.commands.errors import UserInputError


class NoMoveFound(UserInputError):
    def __init__(self, argument: str):
        """Init Method

        Parameters
        ----------
        argument : str
            Invalid String
        """
        self.argument = argument
        super().__init__(f"No Moves with the name {argument!r} were found.")


class NoSpeciesFound(UserInputError):
    def __init__(self, argument: str):
        """Init Method

        Parameters
        ----------
        argument : str
            Invalid String
        """
        self.argument = argument
        super().__init__(f"No Species with the name {argument!r} were found.")


class NoImageFound(UserInputError):
    def __init__(self, argument: str):
        """Init Method

        Parameters
        ----------
        argument : str
            Invalid String
        """
        self.argument = argument
        super().__init__(f"No file with the url {argument!r} was found.")


class NoDateFound(UserInputError):
    def __init__(self, argument: str):
        """Init Method

        Parameters
        ----------
        argument : str
            Invalid String
        """
        self.argument = argument
        super().__init__(f"No date {argument!r} was found.")


class SubmissionConcluded(Exception):
    """
    This represents an exception related to concluding a character creation
    """

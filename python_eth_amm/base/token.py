import json
from pathlib import Path
from typing import Any, Dict, Optional, Union

from eth_typing import ChecksumAddress
from eth_utils import is_checksum_address, to_checksum_address
from pydantic import BaseModel
from web3 import Web3


class ERC20Token(BaseModel):
    """
    Class for representing ERC20 Tokens.  Can be initialized from on-chain token, and will query
    token constants from contract.

    Can be used to convert raw token amounts into human-readable amounts.
    """

    name: str
    """
        UTF-8 Name of the token from Token Contract
    """

    symbol: str
    """
        Token Symbol from Contract
    """

    decimals: int
    """
        Number of decimals from Token Contract
    """

    address: ChecksumAddress
    """
        Checksum Address of the Token Contract
    """

    contract: Optional[object] = None
    """
        Returns :class:`~web3.eth.Contract if token was initialized from on-chain token`
    """

    @classmethod
    def from_chain(
        cls,
        w3: Web3,  # pylint: disable=invalid-name
        token_address: Union[ChecksumAddress, str],
    ) -> "ERC20Token":
        """
        Initialize ERC20Token from on-chain token address.  Fetches token name, symbol, and decimals from contract.
        If token_address is invalid, raises ___

        :param w3:
            :class:`~web3.Web3` RPC connection to EVM node
        :param token_address:
            hex address of ERC20 token contract
        :return: :class:`~python_eth_amm.base.token.ERC20Token`
        """
        if not is_checksum_address(token_address):
            token_address = to_checksum_address(token_address)

        token_contract = w3.eth.contract(token_address, abi=cls.get_abi())
        return ERC20Token(
            name=token_contract.functions.name().call(),
            symbol=token_contract.functions.symbol().call(),
            decimals=token_contract.functions.decimals().call(),
            address=token_address,
            contract=token_contract,
        )

    @classmethod
    def get_abi(cls, json_string: Optional[bool] = False) -> Union[Dict[str, Any], str]:
        """
        Returns ABI for ERC20 Token Contract.

        :param bool json_string:
            If true, returns ABI as a JSON string.  Otherwise, returns ABI as a dictionary.

            Default: False
        :return:
        """
        with open(
            Path(__file__).parent.joinpath("ERC20ABI.json"), "r", encoding="utf-8"
        ) as json_file:
            abi = json.load(json_file)
        if json_string:
            return json.dumps(abi)
        return abi

    @classmethod
    def default_token(cls, token_number) -> "ERC20Token":
        """
        Returns an empty token with default values.  Used when initializing an empty test pool.
        :param token_number: 0-9 integer that is used in the token name, symbol, and address
        :return:
        """
        return ERC20Token(
            name=f"Default Token {token_number}",
            symbol=f"TKN{token_number}",
            decimals=18,
            address=to_checksum_address("0x" + str(token_number) * 40),
        )

    def convert_decimals(self, raw_token_amount: int) -> float:
        """
        Divides raw token amounts by token decimals.

        :param int raw_token_amount:
            Raw token amount
        :return:
            Token amount adjusted by decimals
        """
        return raw_token_amount / 10**self.decimals

    def human_readable(self, raw_token_amount: int) -> str:
        """
        Converts raw token amount to human-readable string containing the correct decimals and the token symbol.

        :param raw_token_amount:
            raw token amount
        :return:
            Human-readable string containing token amount and symbol
        """

        return f"{self.convert_decimals(raw_token_amount)} {self.symbol}"

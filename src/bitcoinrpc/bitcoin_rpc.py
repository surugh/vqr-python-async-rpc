import itertools
from types import TracebackType
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union

import httpx
import orjson
from typing_extensions import Literal, Self

from bitcoinrpc._exceptions import RPCError
from bitcoinrpc._types import (
    AnalyzePSBT,
    BestBlockHash,
    BitcoinRPCResponse,
    Block,
    BlockchainInfo,
    BlockCount,
    BlockHash,
    BlockHeader,
    BlockStats,
    ChainTips,
    CombinePSBT,
    ConnectionCount,
    DecodePSBT,
    Difficulty,
    FinalizePSBT,
    JoinPSBTs,
    JSONType,
    MempoolInfo,
    MiningInfo,
    NetworkHashps,
    NetworkInfo,
    RawTransaction,
    UtxoUpdatePSBT,
    WalletProcessPSBT,
    SendToAddress,
    ListRecievedByAddress
)

# Neat trick found in asyncio library for task enumeration
# https://github.com/python/cpython/blob/3.8/Lib/asyncio/tasks.py#L31
_next_rpc_id = itertools.count(1).__next__


class VqrcoinRPC:
    __slots__ = ("_url", "_client", "_counter")
    """
    Class representing a JSON-RPC client of a Bitcoin node.

    :param url: URL of the Bitcoin node.
    :param client: Underlying `httpx.AsyncClient`, 
        which handles the requests issued.
    :param counter: Optional callable that serves as a generator 
        for the "id" field within JSON-RPC requests.

    For list of all available commands, visit:
    https://developer.bitcoin.org/reference/rpc/index.html
    """

    def __init__(
        self,
        url: str,
        client: httpx.AsyncClient,
        counter: Callable[[], Union[int, str]] = _next_rpc_id,
    ) -> None:
        self._url = url
        self._client = client
        self._counter = counter

    async def __aenter__(self) -> "VqrcoinRPC":
        return self

    async def __aexit__(
        self,
        exc_type: Type[BaseException],
        exc_val: BaseException,
        exc_tb: TracebackType,
    ) -> None:
        await self.aclose()

    @classmethod
    def from_config(
        cls,
        url: str,
        auth: Optional[Tuple[str, str]],
        **options: Any,
    ) -> Self:
        """
        Instantiate the `VqrcoinRPC` client while also configuring
        the underlying `httpx.AsyncClient`.
        Additional options are passed directly as kwargs to `httpx.AsyncClient`,
        so it's your responsibility to conform to its interface.
        """

        options = dict(options)
        headers = {
            "content-type": "application/json",
            **dict(options.pop("headers", {})),
        }
        return cls(
            url, httpx.AsyncClient(auth=auth, headers=headers, **options)
        )

    @property
    def url(self) -> str:
        return self._url

    @property
    def client(self) -> httpx.AsyncClient:
        return self._client

    async def aclose(self) -> None:
        await self.client.aclose()

    async def acall(
        self,
        method: str,
        params: List[JSONType],
        **kwargs: Any,
    ) -> BitcoinRPCResponse:
        """
        Pass keyword arguments to directly modify the constructed request -
            see `httpx.Request`.
        """
        response = await self.client.post(
            url=self.url,
            content=orjson.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": self._counter(),
                    "method": method,
                    "params": params,
                }
            ),
            **kwargs,
        )

        # Raise an exception if return code is not in 2xx range
        # https://www.python-httpx.org/quickstart/#exceptions
        response.raise_for_status()

        content = orjson.loads(response.content)
        if content["error"] is not None:
            raise RPCError(
                content["error"]["code"], content["error"]["message"]
            )
        else:
            return content["result"]

    """Wallet"""
    async def listreceivedbyaddress(
        self,
        include_watchonly: Optional[bool],
        address_filter: Optional[str],
        include_empty: Optional[bool] = False,
        minconf: Optional[int] = 1,
    ) -> List[ListRecievedByAddress]:
        """
        https://developer.bitcoin.org/reference/rpc/listreceivedbyaddress.html

        :param minconf: The minimum number of confirmations
            before payments are included.
        :param include_empty: Whether to include addresses
            that haven't received any payments.
        :param include_watchonly: Whether to include watch-only addresses
        :param address_filter If present, only return information on this address.
        """
        return await self.acall(
            "listreceivedbyaddress",
            [minconf, include_empty, include_watchonly, address_filter],
        )

    async def importpubkey(
        self, pubkey: str, label: Optional[str], rescan: Optional[bool] = True
    ) -> None:
        """
        https://developer.bitcoin.org/reference/rpc/importpubkey.html

        :param pubkey: The hex-encoded public key.
        :param label: An optional label.
        :param rescan: Rescan the wallet for transactions
        """
        return await self.acall("importpubkey", [pubkey, label, rescan])

    async def getnewaddress(
        self,
        label: Optional[str] = None,
        address_type: Optional[str] = "legacy"
    ) -> str:
        """
        https://developer.bitcoin.org/reference/rpc/getnewaddress.html

        :param label: The label name for the address to be linked to.
            It can also be set to the empty string “”
            to represent the default label.
            The label does not need to exist,
            it will be created if there is no label by the given name.
        :param address_type: The address type to use.
            Options are “legacy”, “p2sh-segwit”, and “bech32”.
        """
        return await self.acall("getnewaddress", [label, address_type])

    async def sendtoaddress(
            self,
            address: str,
            amount: float,
            comment: Optional[str] = None,
            comment_to: Optional[str] = None,
            subtractfeefromamount: Optional[bool] = True,
            avoid_reuse: Optional[bool] = False,
    ) -> SendToAddress:
        """
        https://developer.bitcoin.org/reference/rpc/sendtoaddress.html

        :param address: The coin address to send to.
        :param amount: The amount in coin to send. eg 0.1
        :param comment: A comment used to store what the transaction is for.
            This is not part of the transaction, just kept in your wallet.
        :param comment_to: A comment to store the name of the person or
            organization to which you're sending the transaction.
            This is not part of the transaction, just kept in your wallet.
        :param subtractfeefromamount: The fee will be deducted from the amount being sent.
            The recipient will receive less coins than you enter in the amount field.
        :param avoid_reuse: (only available if avoid_reuse wallet flag is set)
            Avoid spending from dirty addresses; addresses are considered
            dirty if they have previously been used in a transaction.
        """
        return await self.acall(
            "sendtoaddress",
            [address, amount, comment, comment_to, subtractfeefromamount,
             avoid_reuse],
        )

    async def walletprocesspsbt(
            self,
            psbt: str,
            sign: bool = True,
            sighashtype: str = "ALL",
            bip32_derivs: bool = True,
    ) -> WalletProcessPSBT:
        """
        https://developer.bitcoin.org/reference/rpc/walletprocesspsbt.html

        :param psbt: base64 string of a partially signed bitcoin transaction
        :param sign: Sign the transaction too when updating
        :param sighashtype: signature hash type to sign,
            if it is not specified by PSBT.
        :param bip32_derivs: include bip32 derivation paths for pubkeys if known
        """
        return await self.acall(
            "walletprocesspsbt", [psbt, sign, sighashtype, bip32_derivs]
        )

    """Blockchain"""
    async def getmempoolinfo(self) -> MempoolInfo:
        """https://developer.bitcoin.org/reference/rpc/getmempoolinfo.html"""
        return await self.acall("getmempoolinfo", [])

    async def getblockchaininfo(self) -> BlockchainInfo:
        """https://developer.bitcoin.org/reference/rpc/getblockchaininfo.html"""
        return await self.acall("getblockchaininfo", [])

    async def getchaintips(self) -> ChainTips:
        """https://developer.bitcoin.org/reference/rpc/getchaintips.html"""
        return await self.acall("getchaintips", [])

    async def getdifficulty(self) -> Difficulty:
        """https://developer.bitcoin.org/reference/rpc/getdifficulty.html"""
        return await self.acall("getdifficulty", [])

    async def getbestblockhash(self) -> BestBlockHash:
        """https://developer.bitcoin.org/reference/rpc/getbestblockhash.html"""
        return await self.acall("getbestblockhash", [])

    async def getblockhash(self, height: int) -> BlockHash:
        """https://developer.bitcoin.org/reference/rpc/getblockhash.html"""
        return await self.acall("getblockhash", [height])

    async def getblockcount(self) -> BlockCount:
        """https://developer.bitcoin.org/reference/rpc/getblockcount.html"""
        return await self.acall("getblockcount", [])

    async def getblockheader(
        self,
        block_hash: str,
        verbose: bool = True
    ) -> BlockHeader:
        """https://developer.bitcoin.org/reference/rpc/getblockheader.html"""
        return await self.acall("getblockheader", [block_hash, verbose])

    async def getblockstats(
        self,
        hash_or_height: Union[int, str],
        *keys: str,
        timeout: Optional[float] = 5.0,
    ) -> BlockStats:
        """
        https://developer.bitcoin.org/reference/rpc/getblockstats.html

        Enter `keys` as positional arguments to return only the provided `keys`
            in the response.
        """
        return await self.acall(
            "getblockstats",
            [hash_or_height, list(keys) or None],
            timeout=httpx.Timeout(timeout),
        )

    async def getblock(
        self,
        block_hash: str,
        verbosity: Literal[0, 1, 2] = 1,
        timeout: Optional[float] = 5.0,
    ) -> Block:
        """
        https://developer.bitcoin.org/reference/rpc/getblock.html

        :param block_hash: The block hash
        :param verbosity: 0 for hex-encoded block data, 1 for block data with
            transactions list, 2 for block data with each transaction.
        :param timeout: Timeout optional
        """
        return await self.acall(
            "getblock", [block_hash, verbosity], timeout=httpx.Timeout(timeout)
        )

    async def getnetworkhashps(
        self,
        nblocks: int = -1,
        height: Optional[int] = None,
        timeout: Optional[float] = 5.0,
    ) -> NetworkHashps:
        """
        https://developer.bitcoin.org/reference/rpc/getnetworkhashps.html

        :param nblocks: -1 for estimated hash power since last difficulty change,
            otherwise as an average over last provided number of blocks
        :param height: If not provided,
            get estimated hash power for the latest block
        :param timeout: If doing a lot of processing,
            no timeout may come in handy
        """
        return await self.acall(
            "getnetworkhashps", [nblocks, height], timeout=httpx.Timeout(timeout)
        )

    """Mining"""
    async def getmininginfo(self) -> MiningInfo:
        """https://developer.bitcoin.org/reference/rpc/getmininginfo.html"""
        return await self.acall("getmininginfo", [])

    """Network"""
    async def getconnectioncount(self) -> ConnectionCount:
        """https://developer.bitcoin.org/reference/rpc/getconnectioncount.html"""
        return await self.acall("getconnectioncount", [])

    async def getnetworkinfo(self) -> NetworkInfo:
        """https://developer.bitcoin.org/reference/rpc/getnetworkinfo.html"""
        return await self.acall("getnetworkinfo", [])

    """Raw transactions"""
    async def analyzepsbt(self, psbt: str) -> AnalyzePSBT:
        """
        https://developer.bitcoin.org/reference/rpc/analyzepsbt.html

        :param psbt: base64 string of a partially signed bitcoin transaction
        """
        return await self.acall("analyzepsbt", [psbt])

    async def combinepsbt(self, *psbts: str) -> CombinePSBT:
        """
        https://developer.bitcoin.org/reference/rpc/combinepsbt.html

        :param psbts: base64 strings,
            each representing a partially signed bitcoin transaction
        """
        return await self.acall("combinepsbt", list(psbts))

    async def decodepsbt(self, psbt: str) -> DecodePSBT:
        """
        https://developer.bitcoin.org/reference/rpc/decodepsbt.html

        :param psbt: base64 string of a partially signed bitcoin transaction
        """
        return await self.acall("decodepsbt", [psbt])

    async def finalizepsbt(
            self,
            psbt: str,
            extract: bool = True
    ) -> FinalizePSBT:
        """
        https://developer.bitcoin.org/reference/rpc/finalizepsbt.html

        :param psbt: base64 string of a partially signed bitcoin transaction
        :param extract: If set to true and the transaction is complete,
            return a hex-encoded network transaction
        """
        return await self.acall("finalizepsbt", [psbt, extract])

    async def getrawtransaction(
        self,
        txid: str,
        verbose: bool = True,
        block_hash: Optional[str] = None,
        timeout: Optional[float] = 5.0,
    ) -> RawTransaction:
        """
        https://developer.bitcoin.org/reference/rpc/getrawtransactiono.html

        :param txid: If transaction is not in mempool,
            block_hash must also be provided.
        :param verbose: True for JSON, False for hex-encoded string
        :param block_hash: see ^txid
        :param timeout: If doing a lot of processing,
            no timeout may come in handy
        """
        return await self.acall(
            "getrawtransaction",
            [txid, verbose, block_hash],
            timeout=httpx.Timeout(timeout),
        )

    async def joinpsbts(self, *psbts: str) -> JoinPSBTs:
        """
        https://developer.bitcoin.org/reference/rpc/joinpsbts.html

        :param psbts: base64 strings,
            each representing a partially signed bitcoin transaction
        """
        return await self.acall("joinpsbts", list(psbts))

    async def utxoupdatepsbt(
        self,
        psbt: str,
        descriptors: Optional[
            List[Union[str, Dict[str, Union[int, str]]]]
        ] = None
    ) -> UtxoUpdatePSBT:
        """
        https://developer.bitcoin.org/reference/rpc/utxoupdatepsbt.html

        :param psbt: base64 string of a partially signed bitcoin transaction
        :param descriptors: An array of either strings or objects
        """
        if descriptors is not None:
            params = [psbt, descriptors]
        else:
            params = [psbt]
        return await self.acall("utxoupdatepsbt", params)  # type: ignore

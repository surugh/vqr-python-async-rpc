# vqr-python-async-rpc
Lightweight VQR async JSON-RPC Python client.

Serves as a tiny layer between an application and a VQRcoin daemon, its primary usage
is querying the current state of VQRcoin blockchain, network stats, transactions...

If you want complete Bitcoin experience in Python, consult
[python-bitcoinlib](https://github.com/petertodd/python-bitcoinlib).

## Installation
```bash
$ pip install vqrcoinrpc
```

## Supported methods
Here is a list of supported methods, divided by their categories. Should you need
method not implemented, wrap the call in `VqrcoinRPC.acall(<your_method>, ...)` coroutine.

### Blockchain

| Method              | Supported? |
|---------------------|:----------:|
| `getbestblockhash`  |     ✔      |
| `getblock`          |     ✔      |
| `getblockchaininfo` |     ✔      |
| `getblockcount`     |     ✔      |
| `getblockhash`      |     ✔      |
| `getblockheader`    |     ✔      |
| `getblockstats`     |     ✔      |
| `getchaintips`      |     ✔      |
| `getdifficulty`     |     ✔      |
| `getmempoolinfo`    |     ✔      |
| `getnetworkhashps`  |     ✔      |

### Mining

| Method          | Supported? |
|-----------------|:----------:|
| `getmininginfo` |     ✔      |

### Network

| Method               | Supported? |
|----------------------|:----------:|
| `getconnectioncount` |     ✔      |
| `getnetworkinfo`     |     ✔      |

### Raw transactions

| Method              | Supported? |
|---------------------|:----------:|
| `analyzepsbt`       |     ✔      |
| `combinepsbt`       |     ✔      |
| `decodepsbt`        |     ✔      |
| `finalizepsbt`      |     ✔      |
| `getrawtransaction` |     ✔      |
| `joinpsbts`         |     ✔      |
| `utxoupdatepsbt`    |     ✔      |

### Wallet

| Method                         | Supported? |
|--------------------------------|:----------:|
| `getbalance`                   |     ✔      |
| `getwalletinfo`                |     ✔      |
| `listaddressgroupings`         |     ✔      |
| `sendtoaddress`                |     ✔      |
| `importpubkey`                 |     ✔      |
| `getnewaddress`                |     ✔      |
| `listreceivedbyaddress`        |     ✔      |
| `listunspent`                  |     ✔      |
| `signrawtransactionwithwallet` |     ✔      |
| `createwallet`                 |     ✔      |
| `walletpassphrase`             |     ✔      |
| `walletprocesspsbt`            |     ✔      |

## Usage
Minimal illustration (assuming Python 3.8+, where you can run `async` code in console)
listreceivedbyaddress
```
$ python -m asyncio
>>> import asyncio
>>>
>>> from vqrcoinrpc import VqrcoinRPC
>>> rpc = VqrcoinRPC.from_config("http://localhost:7332", ("rpc_user", "rpc_passwd"))
>>> await rpc.getconnectioncount()
10
>>> await rpc.aclose()  # Clean-up resource
```

You can also use the `VqrcoinRPC` as an asynchronous context manager, which does
all the resource clean-up automatically, as the following example shows:

$ cat
vqr_rpc_minimal.py

```python

import asyncio

from vqrcoinrpc import VqrcoinRPC


async def main():
  async with VqrcoinRPC.from_config("http://localhost:7332",
                                    ("rpc_user", "rpc_password")) as rpc:
    print(await rpc.getconnectioncount())


if __name__ == "__main__":
  asyncio.run(main())
```

Running this script yields:
```
$ python vqr_rpc_minimal.py
10
```

If you want customize the underlying `httpx.AsyncClient`, you can instantiate the `VqrcoinRPC` with one.
Consider the following script, where the client is configured to log every HTTP request before it is sent
out over the wire:

$ cat
vqr_custom_client.py

```python

import asyncio

import httpx

from vqrcoinrpc import VqrcoinRPC


async def log_request(request: httpx.Request) -> None:
  print(request.content)


async def main() -> None:
  client = httpx.AsyncClient(auth=("rpc_user", "rpc_password"),
                             event_hooks={"request": [log_request]})
  async with VqrcoinRPC(url="http://localhost:7332", client=client) as rpc:
    print(await rpc.getconnectioncount())


if __name__ == "__main__":
  asyncio.run(main())
```

Running this script yields:

```
$ python vqr_custom_client.py 
b'{"jsonrpc":"2.0","id":1,"method":"getconnectioncount","params":[]}'
0
```

## Testing

A `Containerfile` is provided as a means to build an OCI image of a Bitcoin `regtest` node.
Build the image (`podman` is used, but `docker` should be fine too):

```
$ podman build \
  -f Containerfile \
  --build-arg BTC_VERSION=v24.1 \
  -t bitcoin-regtest:v24.1 \
  -t bitcoin-regtest:latest \
  .
```

and run it afterwards:

```
$ podman run \
  --rm \
  -it \
  --mount=type=bind,src=./tests/bitcoin-regtest.conf,target=/home/rpc/.bitcoin/bitcoin.conf \
  -p 127.0.0.1:18443:18443 \
  --name bitcoin-regtest \
  localhost/bitcoin-regtest:v24.1
```

which will expose the Bitcoin `regtest` node on port 18443, accesible from localhost only, with RPC user/password `rpc_user/rpc_password`.

After you are done testing, stop the container via:

```
$ podman stop bitcoin-regtest
```

---

If you want to test against a different version of Bitcoin node, pass a different [tag](https://github.com/bitcoin/bitcoin/tags) in the build stage:

```
$ podman build \
  -f Containerfile \
  --build-arg BTC_VERSION=v25.0 \
  -t bitcoin-regtest:v25.0 \
  -t bitcoin-regtest:latest \
  .
```

---

Different settings of the Bitcoin node may be passed via mounting your custom configuration file, or optionally as "arguments" to `podman run`:


```
$ podman run \
  --rm \
  -it \
  --mount=type=bind,src=<path/to/your/config_file>,target=/home/rpc/.bitcoin/bitcoin.conf \
  -p 127.0.0.1:18443:18443 \
  --name bitcoin-regtest \
  localhost/bitcoin-regtest:v24.1 <your> <args> ...
```

---

Please, keep in mind that Bitcoin node compiled in the image is intended for testing & debugging purposes only! It may serve you as an inspiration for building
your own, production-ready Bitcoin node, but its intended usage is testing!

---

For testing this library, install `tox` (preferably, in a fresh virtual environment).

Afterwards, coding-style is enforced by running:

```
(your-venv-with-tox) $ tox run -e linters
```

and tests corresponding are run (this example uses Python3.11)

```
(your-venv-with-tox) $ tox run -e py311
```

If you do not want to run tests marked as `"integration"`, which denote those requiring the bitcoin regtest node to run, you can filter them out by:

```
(your-venv-with-tox) $ tox run -e py311 -- -m 'not integration'
```


## Changelog

- **2024/01/13 - 0.6.3**: Fix wallet RPC methods
- **2024/01/13 - 0.6.3**: Add wallet RPC methods
- **2024/01/13 - 0.6.2**: Add wallet RPC methods, from *coin fork
- **2023/06/04 - 0.6.1**: Add RPC methods, mainly concerned with PSBTs
- **2023/06/01 - 0.6.0**:
  * `VqrcoinRPC` is now instantiated with a `httpx.AsyncClient` directly and an optional `counter` argument, which is a callable that may be used for distinguishing
    the JSON-RPC requests. Old-style instantiation, with `url` and optional user/password tuple, is kept within `VqrcoinRPC.from_config` method.

- **2021/12/28 - 0.5.0** change the signature of `VqrcoinRPC` from `host, port, ...` to `url, ...`, delegating the creation of the node url to the caller.

## License
MIT

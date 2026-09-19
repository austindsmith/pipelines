import asyncio

from onepassword.client import Client

from bills.core.settings import OP_SERVICE_ACCOUNT_TOKEN


async def main():
    client = await Client.authenticate(
        auth=OP_SERVICE_ACCOUNT_TOKEN,
        integration_name="bills",
        integration_version="0.1.0",
    )

    password = await client.secrets.resolve(
        "op://utilities/ABQ Water Authority/password"
    )

    print(password)


if __name__ == "__main__":
    asyncio.run(main())

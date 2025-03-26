import aiohttp
import asyncio
from urllib.parse import urlencode

BILLMGR_URL = "https://my.firstvds.ru"
AUTH_INFO = "tarasov@cloudsell.ru:uL6jH4eW3poP4v"


async def order_vds(pricelist_id, os_template, period="monthly", domain=None, autoprolong=0, remoteid=0, skipbasket=True, recipe=None):
    period_map = {
        'trial': '-100', 'daily': '-50', 'monthly': '1', 'quarterly': '3',
        'semi-annual': '6', 'annual': '12', 'biennial': '24', 'triennial': '36', 'one-time': '0'
    }
    params = {
        "func": "vds.order.param",
        "authinfo": AUTH_INFO,
        "ostempl": os_template,
        "period": period_map[period],
        "pricelist": pricelist_id,
        "autoprolong": autoprolong,
        "remoteid": remoteid,
        "sok": "ok"
    }

    if domain:
        params["domain"] = domain
    if skipbasket:
        params["skipbasket"] = "on"
    if recipe:
        params["recipe"] = recipe

    query_string = urlencode(params)
    url = f"{BILLMGR_URL}/billmgr?{query_string}"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                print(f"Error: Received status code {response.status}")
                return None
            try:
                print(response)
                return await response.json()
            except Exception as e:
                print(f"Error parsing JSON: {e}")
                return None


if __name__ == "__main__":
    response = asyncio.run(order_vds(
        remoteid=777,
        pricelist_id=18140,
        os_template="VM6_ISPsystem_Ubuntu-20.04",
        period="daily",
        domain="vds.test",
        recipe="VM6_ISPsystem_LAMP_5"
    ))
    if response:
        print(response)
    else:
        print("No response or error.")

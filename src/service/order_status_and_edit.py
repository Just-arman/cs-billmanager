import aiohttp
import asyncio
from urllib.parse import urlencode
from src.logger import log

BILLMGR_URL = "https://billing.spacecore.pro"
AUTH_INFO = "tarasov@cloudsell.ru:fD2bG7kH8jbV6nW"

status_map = {
    '0': 'Неизвестен',
    '1': 'Заказан',
    '2': 'Активен',
    '3': 'Остановлен',
    '4': 'Удален',
    '5': 'Обрабатывается'
}
period_map = {
    'trial': '-100', 'daily': '-50', 'monthly': '1', 'quarterly': '3',
    'semi-annual': '6', 'annual': '12', 'biennial': '24', 'triennial': '36', 'one-time': '0'
}

async def get_order_data():
    params = {
        "authinfo": AUTH_INFO,
        "func": "vds",
        "out": "json"
    }

    query_string = urlencode(params)
    url = f"{BILLMGR_URL}/billmgr?{query_string}"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                log.info(f"Error: Received status code {response.status}")
                return None
            try:
                data = await response.json()
                return data
            except Exception as e:
                log.info(f"Error parsing JSON: {e}")
                return None

async def get_order_status(remoteid):
    order_data = await get_order_data()
    if order_data is None:
        return None

    elements = order_data.get('doc', {}).get('elem', [])
    if not elements:
        log.info("Ошибка: Не найден elem в ответе.")
        return None

    for elem in elements:
        elem_remoteid = elem.get('remoteid', {}).get('$')
        if str(elem_remoteid) == str(remoteid):    
            status_code = elem.get('status', {}).get('$')
            if status_code is None:
                log.info("Ошибка: Не найден статус для указанного remoteid.")
                return None
            log.info(status_code)
            return status_map.get(status_code, 'Неизвестен')

    log.info(f"Ошибка: Не найден заказ с remoteid {remoteid}.")
    return None

async def prolong_order(
    remoteid: int, 
    period: str, 
    expiredate: str, 
    real_expiredate: str, 
    iexpiretime: str, 
    transition: str, 
    skipbasket: bool=True
):
    order_data = await get_order_data()
    if order_data is None:
        log.info(f"Не удалось получить данные о заказах. Продление невозможно.")
        return None

    elements = order_data.get('doc', {}).get('elem', [])
    if not elements:
        log.info(f"Ошибка: Не найден elem в ответе при продлении заказа {remoteid}.")
        return None

    for elem in elements:
        elem_remoteid = elem.get('remoteid', {}).get('$')
        if str(remoteid) in str(elem_remoteid):
            current_period = elem.get('period', {}).get('$')
            log.info(f"Текущий период: {current_period}")
            if current_period is None:
                log.info(f"Ошибка: не найден период для продления сервера {remoteid}.")
                return None

            params = {
                "authinfo": AUTH_INFO,
                "func": "vds.edit", 
                "remoteid": remoteid,
                "expiredate": expiredate,
                "real_expiredate": real_expiredate,
                "i_expiretime": iexpiretime,
                "period": period_map[period],
                "transition": transition,
                "autoprolong": "on",
                "sok": "ok",
                "out": "json"
            }
            if skipbasket:
                params["skipbasket"] = "on"
            query_string = urlencode(params)
            url = f"{BILLMGR_URL}/billmgr?{query_string}"

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        log.info(f"Ошибка продления: код ответа {response.status}")
                        return None
                    try:
                        response = await response.json()
                        log.info(f"{url=}")
                        return response
                    except Exception as e:
                        log.info(f"Ошибка при продлении заказа: {e}")
                        return None

    log.info(f"Ошибка: Не найден заказ с remoteid {remoteid} для продления.")
    return None

if __name__ == "__main__":
    status = asyncio.run(get_order_status(
        remoteid=888
    ))
    if status:
        log.info(f"Статус заказа: {status}")
    else:
        log.info("Не удалось получить статус заказа.")
    
    result = asyncio.run(prolong_order(
        remoteid=888,
        period="daily",
        expiredate="2025-04-07 20:00",
        real_expiredate="2025-04-07",
        iexpiretime="20:00",
        transition="on"
    ))
    if result:
        log.info(result)
    else:
        log.info("Продление сервера не удалось.")
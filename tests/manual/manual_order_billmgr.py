import asyncio

from pytest import param
from src.service.order_billmgr import OrderHandler, period_map
from src.logger import log
from config import base_url, auth_info


async def main():
    order_handler = OrderHandler(base_url, auth_info)
    await order_handler.open_session()
    try:
        # func = "vds.order.param"
        func = "v2.vds.order.param"
        clicked_button = "order"
        pricelist_id = 18140
        autoprolong = "off"
        os_template = "VM6_ISPsystem_Ubuntu-20.04"
        order_period = "-50"
        domain = "vds.test"
        recipe = "VM6_ISPsystem_LAMP_5"
        params = {
            "clicked_button": clicked_button,
            "pricelist": pricelist_id,
            "autoprolong": autoprolong,
            "os_template": os_template,
            "order_period": order_period,
            "domain": domain,
            "recipe": recipe,
        }
        # # Оформление заказа
        # response = await order_handler.order_vds(
        #     func=func,
        #     clicked_button=clicked_button,
        #     pricelist_id=pricelist_id,
        #     os_template=os_template,
        #     order_period=order_period,
        #     domain=domain,
        #     autoprolong=autoprolong,
        #     recipe=recipe
        # )
        # if response:
        #     log.info(f"Ответ на заказ: {response}")
        #     remoteid = int(response.get("remoteid", 777))  # Получаем remoteid, если есть
        # else:
        #     log.info("Нет ответа или ошибка.")
        #     remoteid = 777

        get_docs = await order_handler.get_orders(func=func)
        log.info(f"{get_docs=}")

        # Получение статуса заказа
        current_status = await order_handler.get_order_status(
            func=func,
            clicked_button="order",
            pricelist_id=18140, 
            autoprolong="off", 
            remoteid=777,
            elid=331863,
            order_period ="-50",
            status='on',
        )
        log.info(f"{current_status=}")

        update_response = await order_handler.update_order_status(
            func=func,
            clicked_button="order",
            pricelist_id=18140, 
            autoprolong="off", 
            remoteid=777, 
            elid=331863,
            order_period ="-50",
            new_status="stop"
        )
        log.info(f"{update_response=}")

    finally:
        await order_handler.close_session()

if __name__ == "__main__":
    asyncio.run(main())

        # Запуск обновления статуса в фоновом режиме
        # update_task = asyncio.create_task(order_handler.periodic_status_update(
        #     pricelist_id=18140,
        #     autoprolong=0,
        #     remoteid=remoteid,
        #     new_status=new_status,
        #     interval=5
        # ))

        # # Выполним другие действия (например, ещё раз получим статус)
        # await asyncio.sleep(5)  # Симуляция задержки, в это время статус будет обновляться
        # updated_status = await order_handler.get_order_status(pricelist_id=18140, remoteid=remoteid)
        # log.info(f"Обновлённый статус заказа {remoteid}: {updated_status}")

        # # Подождем некоторое время, чтобы увидеть обновления статуса
        # await asyncio.sleep(10)  # Задержка для наблюдения работы обновлений статуса

        # # Завершение работы с задачей обновления
        # update_task.cancel()

#     finally:
#         await order_handler.close_session()

# if __name__ == "__main__":
#     asyncio.run(main())
import aiohttp
import asyncio
import json
import os
from datetime import datetime


async def fetch_data_from_url(session, base_url, auth_data, datacenter_id=None):
    try:
        url = f"{base_url}/billmgr?authinfo={auth_data}&func=v2.vds.order.pricelist&out=json"
        if datacenter_id is not None:
            url += f"&datacenter={datacenter_id}"

        async with session.get(url) as response:
            response.raise_for_status()
            await asyncio.sleep(0.5)
            raw_data = await response.read()
            return json.loads(raw_data.decode('utf-8'))
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None


async def get_datacenters(session, base_url, auth_data):
    data = await fetch_data_from_url(session, base_url, auth_data)
    if data:
        try:
            return [(dc['$key'], dc['$']) for dc in data['doc']['slist'][0]['val']]
        except (KeyError, IndexError) as e:
            print(f"Error extracting datacenters: {e}")
    return []


def get_billing_cycle(period):
    period_map = {
        '-100': 'trial', '-50': 'daily', '1': 'monthly', '3': 'quarterly',
        '6': 'semi-annual', '12': 'annual', '24': 'biennial', '36': 'triennial', '0': 'one-time'
    }
    return period_map.get(str(period['$']), f"{period['$']}_months")


async def fetch_templates_for_plan(session, base_url, auth_data, external_id, debug):
    try:
        url = f"{base_url}/billmgr?authinfo={auth_data}&func=v2.vds.order.param&pricelist={external_id}&period=1&out=json"

        async with session.get(url) as response:
            response.raise_for_status()
            await asyncio.sleep(0.5)
            raw_data = await response.read()
            data = json.loads(raw_data.decode('utf-8'))

            templates = {
                'os_templates': [],
                'app_templates': {}
            }

            if 'slist' in data['doc']:
                for slist in data['doc']['slist']:
                    if slist.get('$name') == 'ostempl' and 'val' in slist:
                        for val in slist['val']:
                            os_template = {
                                'id': val.get('$key', ''),
                                'name': val.get('$', ''),
                                'cost': val.get('$cost', '0.00')
                            }
                            templates['os_templates'].append(os_template)

            if 'slist' in data['doc']:
                for slist in data['doc']['slist']:
                    if slist.get('$name') == 'recipe' and 'val' in slist:
                        for val in slist['val']:
                            if val.get('$key') != 'null' and '$depend' in val:
                                os_id = val.get('$depend', '')
                                app_id = val.get('$key', '')
                                app_name = val.get('$', '')

                                if os_id not in templates['app_templates']:
                                    templates['app_templates'][os_id] = []

                                templates['app_templates'][os_id].append({
                                    'id': app_id,
                                    'name': app_name
                                })

            return templates

    except Exception as e:
        print(f"Error fetching templates for plan {external_id}: {e}")
        return {'os_templates': [], 'app_templates': {}}


def group_os_templates(os_templates):
    grouped_os = {}
    for os_template in os_templates:
        os_name = os_template['name'].lower()
        family = "other"

        if "ubuntu" in os_name:
            family = "ubuntu"
        elif "debian" in os_name:
            family = "debian"
        elif "windows" in os_name:
            family = "windows"
        elif "centos" in os_name:
            family = "centos"
        elif "rocky" in os_name:
            family = "rocky"
        elif "alma" in os_name:
            family = "alma"
        elif "oracle" in os_name:
            family = "oracle"
        elif "freebsd" in os_name:
            family = "freebsd"

        if family not in grouped_os:
            grouped_os[family] = []
        grouped_os[family].append(os_template['id'])

    return grouped_os


def group_app_templates(app_templates, os_templates):
    grouped_apps = {}

    for os_template in os_templates:
        os_name = os_template['name'].lower()
        os_id = os_template['id']
        family = "other"

        if "ubuntu" in os_name:
            family = "ubuntu"
        elif "debian" in os_name:
            family = "debian"
        elif "windows" in os_name:
            family = "windows"
        elif "centos" in os_name:
            family = "centos"
        elif "rocky" in os_name:
            family = "rocky"
        elif "alma" in os_name:
            family = "alma"
        elif "oracle" in os_name:
            family = "oracle"
        elif "freebsd" in os_name:
            family = "freebsd"

        apps = [app['id'] for app in app_templates.get(os_id, [])]

        if apps:
            if family not in grouped_apps:
                grouped_apps[family] = {}

            grouped_apps[family][os_id] = apps

    return grouped_apps


def parse_server_configs(provider_id, data, datacenter_name, templates_data=None):
    servers = []
    server_configs = {}
    try:
        server_list = data['doc']['list'][0]['elem']
        for server_data in server_list:
            external_id = server_data['id']['$']

            details_data = server_data.get('detail', [])
            details = {detail['name']['$']: detail['value']['$'] for detail in details_data} if isinstance(details_data,
                                                                                                           list) else {}

            currency = server_data['prices']['price'][0]['currency']['$'] if server_data['prices']['price'] else '€'

            if external_id not in server_configs:
                server_configs[external_id] = {
                    'name': server_data['title']['$'],
                    'description': server_data.get('description', {}).get('$', ''),
                    'price': {},
                    'currency': currency,
                    'server_type': 'virtual',
                    'provider_id': provider_id,
                    'external_id': external_id,
                    'features': {
                        'processor_name': '',
                        'ram_type': 'DDR4',
                        'cores': details.get('Количество процессоров', '0').split()[0],
                        'ram': details.get('Оперативная память', '0').split()[0],
                        'disk_type': '',
                        'disk': details.get('Дисковое пространство', '0').split()[0],
                        'core_frequency': '',
                        'network_limit': '',
                        'location': datacenter_name,
                        'network_speed': details.get('Входящий трафик', '0')
                    },
                    'additional_info': {'external_id': external_id}
                }

                if templates_data:
                    server_configs[external_id]['available_os'] = group_os_templates(
                        templates_data.get('os_templates', []))
                    server_configs[external_id]['available_apps'] = group_app_templates(
                        templates_data.get('app_templates', {}), templates_data.get('os_templates', []))

            for price_data in server_data['prices']['price']:
                billing_cycle = get_billing_cycle(price_data['period'])
                server_configs[external_id]['price'][billing_cycle] = float(price_data['cost']['$'])

        servers = list(server_configs.values())

    except KeyError as e:
        print(f"Error parsing data for datacenter {datacenter_name}: {e}")
    return servers


async def start_import_plans(provider_id, base_url, auth_data, debug=False):
    async with aiohttp.ClientSession() as session:
        datacenters = await get_datacenters(session, base_url, auth_data)
        if not datacenters:
            print("No datacenters found")
            return []

        all_servers = []

        for dc_id, dc_name in datacenters:
            dc_data = await fetch_data_from_url(session, base_url, auth_data, dc_id)

            if not dc_data:
                print(f"No data found for datacenter {dc_name}")
                continue

            try:
                server_list = dc_data['doc']['list'][0]['elem']
                for server_data in server_list:
                    external_id = server_data['id']['$']

                    templates_data = await fetch_templates_for_plan(session, base_url, auth_data, external_id, debug)

                    server_configs = parse_server_configs(provider_id, {'doc': {'list': [{'elem': [server_data]}]}},
                                                          dc_name, templates_data)
                    all_servers.extend(server_configs)

                    if debug:
                        print(
                            f"Processed plan {server_data['title']['$']} with {len(templates_data.get('os_templates', []))} OS templates")
            except (KeyError, IndexError) as e:
                print(f"Error processing datacenter {dc_name}: {e}")
                continue

        if all_servers and debug:
            save_debug_data(all_servers)
            print(f"Total servers processed: {len(all_servers)}")

        return all_servers


def save_debug_data(data):
    debug_dir = 'debug_data'
    os.makedirs(debug_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{debug_dir}/parsed_data_{timestamp}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Debug data saved to {filename}")


if __name__ == "__main__":
    asyncio.run(start_import_plans(
        provider_id=2,
        base_url="https://my.firstvds.ru",
        auth_data="tarasov@cloudsell.ru:uL6jH4eW3poP4v",
        debug=True
    ))
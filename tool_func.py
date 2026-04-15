import json
import os

import requests
from dotenv import load_dotenv

load_dotenv()
BAIDU_MAP_KEY = os.getenv("BAIDU_MAP_KEY")
QWEATHER_KEY = os.getenv("QWEATHER_KEY")


def _missing_key_error(require_weather: bool = False) -> dict | None:
    missing = []
    if not BAIDU_MAP_KEY:
        missing.append("BAIDU_MAP_KEY")
    if require_weather and not QWEATHER_KEY:
        missing.append("QWEATHER_KEY")
    if missing:
        return {"error": f"缺少 API 密钥，请检查 .env 文件：{', '.join(missing)}"}
    return None


def get_current_location_baidu() -> dict:
    """使用百度 IP 定位 API 获取当前公网 IP 的大致位置"""
    key_error = _missing_key_error()
    if key_error:
        return key_error

    url = "https://api.map.baidu.com/location/ip"
    params = {"ak": BAIDU_MAP_KEY, "coor": "bd09ll"}

    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        res = response.json()
        # print("百度返回：", res)

        if res.get("status") == 0 and res.get("content"):
            content = res["content"]
            point = content.get("point", {})
            detail = content.get("address_detail", {})
            lng = str(point.get("x", ""))
            lat = str(point.get("y", ""))
            address_parts = [
                detail.get("province"),
                detail.get("city"),
                detail.get("district"),
                detail.get("street"),
            ]
            formatted_address = "".join(part for part in address_parts if part) or content.get("address", "")
            return {
                "ip_location": True,
                "ip": content.get("ip", ""),
                "longitude": lng,
                "latitude": lat,
                "location": f"{lng},{lat}" if lng and lat else "",
                "formatted_address": formatted_address,
                "province": detail.get("province"),
                "city": detail.get("city"),
                "district": detail.get("district"),
                "street": detail.get("street"),
                "address": content.get("address", ""),
            }

        return {"error": f"百度定位失败: {res}"}

    except requests.RequestException as e:
        return {"error": f"百度 API 请求失败: {str(e)}"}
    except Exception as e:
        return {"error": f"定位异常: {str(e)}"}


def get_location_baidu(address: str) -> dict:
    """使用百度地理编码 API 查询地点坐标"""
    key_error = _missing_key_error()
    if key_error:
        return key_error

    url = "https://api.map.baidu.com/geocoding/v3/"
    params = {
        "address": address,
        "output": "json",
        "ak": BAIDU_MAP_KEY,
    }

    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        res = response.json()
        # print("百度地理编码返回：", res)

        if res.get("status") == 0 and res.get("result"):
            result = res["result"]
            location = result["location"]
            lng = str(location["lng"])
            lat = str(location["lat"])
            return {
                "longitude": lng,
                "latitude": lat,
                "location": f"{lng},{lat}",
                "formatted_address": address,
            }

        return {"error": f"百度地理编码失败: {res}"}

    except requests.RequestException as e:
        return {"error": f"百度 API 请求失败: {str(e)}"}
    except Exception as e:
        return {"error": f"定位异常: {str(e)}"}


def get_weather_qweather(lon_lat: str, unit: str = "celsius") -> dict:
    """使用和风天气 API 查询实时天气"""
    key_error = _missing_key_error(require_weather=True)
    if key_error:
        return key_error

    url = "https://mn2mtfd4hd.re.qweatherapi.com/v7/weather/now"
    params = {"key": QWEATHER_KEY, "location": lon_lat}

    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        res = response.json()
        # print("和风返回：", res)

        if res.get("code") == "200":
            now = res["now"]
            temp = now["temp"]
            feels_like = now["feelsLike"]
            unit_symbol = "°C"

            if unit == "fahrenheit":
                temp = str(round(float(temp) * 9 / 5 + 32, 1))
                feels_like = str(round(float(feels_like) * 9 / 5 + 32, 1))
                unit_symbol = "°F"

            return {
                "weather": now["text"],
                "temp": f"{temp}{unit_symbol}",
                "feels_like": f"{feels_like}{unit_symbol}",
                "humidity": f"{now['humidity']}%",
                "wind": f"{now['windDir']} {now['windScale']}级",
                "update_time": now["obsTime"],
            }

        error_msgs = {
            "400": "请求参数错误",
            "401": "认证失败，请检查 API 密钥",
            "402": "超过访问次数或余额不足",
            "403": "无权访问该数据",
            "404": "查询地点不存在",
            "429": "请求过于频繁",
        }
        code = res.get("code", "unknown")
        return {"error": error_msgs.get(code, f"查询失败 (代码: {code})")}

    except requests.RequestException as e:
        return {"error": f"和风 API 请求失败: {str(e)}"}
    except Exception as e:
        return {"error": f"天气查询异常: {str(e)}"}


def get_location() -> str:
    loc_res = get_current_location_baidu()
    if "error" in loc_res:
        return json.dumps({"status": "failed", **loc_res}, ensure_ascii=False, indent=2)

    result = {
        "status": "success",
        "address": loc_res["formatted_address"],
        "coordinates": f"{loc_res['latitude']}, {loc_res['longitude']}",
        "longitude": loc_res["longitude"],
        "latitude": loc_res["latitude"],
        "ip": loc_res.get("ip"),
        "province": loc_res.get("province"),
        "city": loc_res.get("city"),
        "district": loc_res.get("district"),
        "street": loc_res.get("street"),
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


def get_weather(city: str, unit: str = "celsius") -> str:
    loc_res = get_location_baidu(city)
    if "error" in loc_res:
        return json.dumps({"status": "failed", **loc_res}, ensure_ascii=False, indent=2)

    weather_res = get_weather_qweather(loc_res["location"], unit)
    result = {
        "status": "success" if "error" not in weather_res else "partial",
        "city": city,
        "address": loc_res["formatted_address"],
        "coordinates": f"{loc_res['latitude']}, {loc_res['longitude']}",
        "weather": weather_res,
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


def execute_tool(tool_name: str, tool_args: dict):
    if tool_name == "get_location":
        return get_location()
    if tool_name == "get_weather":
        return get_weather(tool_args["city"], tool_args.get("unit", "celsius"))

    return json.dumps(
        {"status": "failed", "error": f"未知工具: {tool_name}"},
        ensure_ascii=False,
        indent=2,
    )


if __name__ == "__main__":
    print(get_location())
    print(get_weather("北京"))

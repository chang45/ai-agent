TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市未来 7 天的天气预报，包括每日天气状况、最高温、最低温、湿度和风力等",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称，例如：北京、上海、广州"
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "温度单位，默认摄氏度"
                    }
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_location",
            "description": "获取当前设备公网 IP 对应的大致位置，包括经纬度、城市和地址信息",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    }
]

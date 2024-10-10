import json


async def get_user_study_sheet_data_async(session, api_key):
    url = "https://aaclearningbackend.azurewebsites.net/api/WebAAC/GetUserStudySheetData"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    async with session.get(url, headers=headers) as response:
        if response.status == 200:
            return await response.json()
        else:
            raise Exception(f"GetUserStudySheetData API 調用失敗，狀態碼 {response.status}")


async def get_board_prompt_word_data_async(session, api_key, board_id):
    url = "https://aaclearningbackend.azurewebsites.net/api/WebAAC/GetBoardPromptWordData"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    data = {"ID": board_id}
    async with session.get(url, headers=headers, data=json.dumps(data)) as response:
        if response.status == 200:
            return await response.json()
        else:
            raise Exception(f"GetBoardPromptWordData API 調用失敗，狀態碼 {response.status}")


def parse_user_data(user_data):
    def parse_json_field(field):
        if field:
            try:
                return ", ".join(json.loads(field))
            except json.JSONDecodeError:
                return field
        return "未提供"

    name = parse_json_field(user_data.get("name", "未提供"))
    gender = parse_json_field(user_data.get("gender", "未提供"))
    disability = parse_json_field(user_data.get("disability", "未提供"))
    communication_issues = parse_json_field(user_data.get("communication_Issues", "未提供"))
    communication_methods = parse_json_field(user_data.get("communication_Methods", "未提供"))
    strengths = parse_json_field(user_data.get("strengths", "未提供"))
    weaknesses = parse_json_field(user_data.get("weaknesses", "未提供"))
    teaching_time = parse_json_field(user_data.get("teaching_Time", "未提供"))

    case_info = f"""
    姓名: {name}
    性別: {gender}
    障礙類別: {disability}
    溝通問題: {communication_issues}
    溝通方式: {communication_methods}
    優勢能力: {strengths}
    弱勢能力: {weaknesses}
    預計教學時間: {teaching_time} 分鐘
    """

    return case_info

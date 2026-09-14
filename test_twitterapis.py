import requests

# TwitterAPIs 测试
API_URL = "https://api.twitterapis.com/user/tweets"
HEADERS = {"Authorization": "Bearer test"}  # 需要真实 token

# 测试免费额度注册
print("访问: https://twitterapis.com/signup")
print("获得 $0.50 免费额度（无需信用卡）")
print("\n示例 API 调用:")
print("GET https://api.twitterapis.com/user/tweets?username=elonmusk&count=20")
print("Authorization: Bearer <your_token>")

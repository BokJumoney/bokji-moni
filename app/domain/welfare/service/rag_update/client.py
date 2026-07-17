import asyncio
from xml.parsers.expat import ExpatError

import httpx
import xmltodict

from app.infrastructure.config import settings

async def welfare_list_api_call():
    async with httpx.AsyncClient(timeout=10) as api_client:
        response = await api_client.get(
            "http://apis.data.go.kr/B554287/NationalWelfareInformationsV001/NationalWelfarelistV001",
            params={"serviceKey": settings.WELFARE_API_KEY, "callTP":"D", "pageNo": 1, "numOfRows" : 300, "srchKeyCode":"001", "trgterIndvdlArray":"050"},
        )
        response.raise_for_status()

        return response.text


#신규 정책 상세 API 호출 준비
async def get_new_policy_details(new_policy_list):
    semaphore = asyncio.Semaphore(10)
    async with httpx.AsyncClient(timeout=10) as api_client:
        results = await asyncio.gather(
            *(welfare_detail_api_call(api_client, semaphore, serv_id) for serv_id in new_policy_list)
        )

    return [data for data in results if data is not None]

#신규 정책 상세 API 호출
async def welfare_detail_api_call(api_client, semaphore, serv_id):
    async with semaphore:
        try:
            response = await api_client.get(
                "http://apis.data.go.kr/B554287/NationalWelfareInformationsV001/NationalWelfaredetailedV001",
                params={
                    "serviceKey": settings.WELFARE_API_KEY,
                    "callTP": "D",
                    "servId": serv_id,
                },
            )
            response.raise_for_status()
            return xmltodict.parse(response.text)
        except (httpx.HTTPError, ExpatError) as e:
            print(f"정책 상세 정보 조회 실패 : {serv_id} / {e}")
            return None
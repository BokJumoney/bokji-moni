"""APScheduler 배치 스케줄러 설정.

스케줄러는 "언제 실행할지"만 담당하고, 실제 작업 내용은 서비스 레이어의
함수가 담당한다. 그래서 배치 함수는 스케줄러 없이도 단독 호출(테스트)이
가능하다. lifespan(main.py)에서 start/shutdown 한다.
"""
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

from app.domain.notification.service.noti_service import send_subscription_reminder
from app.infrastructure.config import settings
from app.common.timezone import KST


def create_scheduler() -> AsyncIOScheduler:

    scheduler = AsyncIOScheduler(timezone="Asia/Seoul")

    #시연용
    if settings.REMINDER_DEMO_DELAY_SECONDS:
        run_at = datetime.now(KST) + timedelta(seconds=settings.REMINDER_DEMO_DELAY_SECONDS)
        trigger = DateTrigger(run_date=run_at)
        print(f"[스케줄러] {settings.REMINDER_DEMO_DELAY_SECONDS}초 뒤 실행")
    else:
        trigger = CronTrigger(hour=9)  # 매일 KST기준 09시 정각

    scheduler.add_job(
        send_subscription_reminder,
        trigger,
        id="subscription_reminder",
        coalesce=True,  # 서버가 꺼져 있어 밀린 실행이 쌓여도 1회만 실행
        misfire_grace_time=3600,  # 정시를 놓쳐도 1시간 안이면 실행
    )
    return scheduler

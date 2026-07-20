import subprocess
class CmdExecService:

    async def run_command(self, command: list[str]) -> str:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )
        print("[kordoc] 파싱 완료")

        return result.stdout

import asyncio
import aiohttp
from typing import Optional
from .config import settings
from .logging import get_logger

logger = get_logger(__name__)

class KeepAliveService:
    def __init__(self):
        self.is_running = False
        self.task: Optional[asyncio.Task] = None
        self.health_url = f"{settings.API_BASE_URL}/health"
        
    async def start(self):
        if self.is_running:
            return
            
        self.is_running = True
        self.task = asyncio.create_task(self._keep_alive_loop())
        logger.info("Serviço de keep-alive iniciado")
        
    async def stop(self):
        self.is_running = False
        if self.task and not self.task.done():
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("Serviço de keep-alive parado")
        
    async def _keep_alive_loop(self):
        while self.is_running:
            try:
                await asyncio.sleep(900)  # 15 minutos = 900 segundos
                
                if not self.is_running:
                    break
                    
                await self._ping_health()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Erro no keep-alive loop: {str(e)}")
                
    async def _ping_health(self):
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(self.health_url) as response:
                    if response.status == 200:
                        logger.info("Keep-alive: ping para /health realizado com sucesso")
                    else:
                        logger.warning(f"Keep-alive: ping para /health retornou status {response.status}")
                        
        except Exception as e:
            logger.error(f"Erro ao fazer ping para /health: {str(e)}")

keep_alive_service = KeepAliveService()

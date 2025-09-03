import asyncio
import aiohttp
from typing import Optional
from datetime import datetime
from .config import settings
from .logging import get_logger

logger = get_logger(__name__)

class KeepAliveService:
    def __init__(self):
        self.is_running = False
        self.task: Optional[asyncio.Task] = None
        self.health_url = f"{settings.API_BASE_URL}/health"
        self.ping_interval = 900
        self.ping_count = 0
        
    async def start(self):
        if self.is_running:
            logger.warning("Keep-alive já está rodando, ignorando nova inicialização")
            return
            
        self.is_running = True
        self.ping_count = 0
        
        try:
            self.task = asyncio.create_task(self._keep_alive_loop())
            logger.info(f"Keep-alive iniciado - URL: {self.health_url} - Intervalo: {self.ping_interval}s")
            
            await self._ping_health()
            
        except Exception as e:
            logger.error(f"Erro ao iniciar keep-alive: {str(e)}")
            self.is_running = False
            raise
        
    async def stop(self):
        logger.info("Parando keep-alive...")
        self.is_running = False
        
        if self.task and not self.task.done():
            self.task.cancel()
            try:
                await asyncio.wait_for(self.task, timeout=5.0)
            except asyncio.CancelledError:
                logger.info("Keep-alive parado com sucesso")
            except asyncio.TimeoutError:
                logger.warning("Timeout ao parar keep-alive")
            except Exception as e:
                logger.error(f"Erro ao parar keep-alive: {str(e)}")
                
        logger.info(f"Keep-alive finalizado - Total de pings: {self.ping_count}")
        
    async def _keep_alive_loop(self):
        logger.info("Loop de keep-alive iniciado")
        
        while self.is_running:
            try:
                await asyncio.sleep(self.ping_interval)
                
                if not self.is_running:
                    break
                    
                await self._ping_health()
                
            except asyncio.CancelledError:
                logger.info("Loop de keep-alive cancelado")
                break
            except Exception as e:
                logger.error(f"Erro no loop de keep-alive: {str(e)}")
                await asyncio.sleep(60)
                
        logger.info("Loop de keep-alive finalizado")
                
    async def _ping_health(self):
        start_time = datetime.now()
        self.ping_count += 1
        
        try:
            logger.info(f"Keep-alive ping #{self.ping_count} para {self.health_url}")
            
            timeout = aiohttp.ClientTimeout(total=30)
            connector = aiohttp.TCPConnector(limit=1, limit_per_host=1)
            
            async with aiohttp.ClientSession(
                timeout=timeout, 
                connector=connector,
                headers={'User-Agent': 'KeepAlive-Service/1.0'}
            ) as session:
                async with session.get(self.health_url) as response:
                    duration = (datetime.now() - start_time).total_seconds()
                    
                    if response.status == 200:
                        logger.info(f"Keep-alive ping #{self.ping_count} ✅ SUCESSO - {duration:.2f}s")
                    else:
                        logger.warning(f"Keep-alive ping #{self.ping_count} ⚠️ Status {response.status} - {duration:.2f}s")
                        
        except aiohttp.ClientError as e:
            duration = (datetime.now() - start_time).total_seconds()
            logger.error(f"Keep-alive ping #{self.ping_count} ❌ ERRO HTTP: {str(e)} - {duration:.2f}s")
        except asyncio.TimeoutError:
            duration = (datetime.now() - start_time).total_seconds()
            logger.error(f"Keep-alive ping #{self.ping_count} ⏰ TIMEOUT após {duration:.2f}s")
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            logger.error(f"Keep-alive ping #{self.ping_count} 💥 ERRO: {str(e)} - {duration:.2f}s")

keep_alive_service = KeepAliveService()

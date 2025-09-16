import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from cachetools import TTLCache
import logging

logger = logging.getLogger(__name__)

class NewsCache:
    
    def __init__(self, max_size: int = 100, ttl_seconds: int = 900):
        self.cache = TTLCache(maxsize=max_size, ttl=ttl_seconds)
        self.ttl_seconds = ttl_seconds
        self.stats = {
            "hits": 0,
            "misses": 0,
            "total_requests": 0
        }
        logger.info(f"Cache inicializado: max_size={max_size}, ttl={ttl_seconds}s")
    
    def _generate_cache_key(self, max_noticias: int, filters: Dict = None) -> str:
        key_data = f"noticias:{max_noticias}"
        
        if filters:
            filter_str = json.dumps(filters, sort_keys=True, ensure_ascii=False)
            key_data += f":filters:{filter_str}"
        
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, max_noticias: int, filters: Dict = None) -> Optional[Dict[str, Any]]:
        self.stats["total_requests"] += 1
        cache_key = self._generate_cache_key(max_noticias, filters)
        
        try:
            cached_data = self.cache.get(cache_key)
            if cached_data is not None:
                self.stats["hits"] += 1
                filter_info = " com filtros" if filters else ""
                logger.info(f"Cache HIT para {max_noticias} notícias{filter_info}")
                return cached_data
            else:
                self.stats["misses"] += 1
                filter_info = " com filtros" if filters else ""
                logger.info(f"Cache MISS para {max_noticias} notícias{filter_info}")
                return None
        except Exception as e:
            logger.error(f"Erro ao acessar cache: {e}")
            self.stats["misses"] += 1
            return None
    
    def set(self, max_noticias: int, data: Dict[str, Any], filters: Dict = None) -> None:
        cache_key = self._generate_cache_key(max_noticias, filters)
        
        try:
            data_with_cache_info = {
                **data,
                "cache_info": {
                    "cached_at": datetime.now().isoformat(),
                    "expires_at": (datetime.now() + timedelta(seconds=self.ttl_seconds)).isoformat(),
                    "from_cache": True
                }
            }
            
            self.cache[cache_key] = data_with_cache_info
            filter_info = " com filtros" if filters else ""
            logger.info(f"Dados armazenados no cache para {max_noticias} notícias{filter_info}")
            
        except Exception as e:
            logger.error(f"Erro ao armazenar no cache: {e}")
    
    def clear(self) -> None:
        self.cache.clear()
        logger.info("Cache limpo manualmente")
    
    def get_stats(self) -> Dict[str, Any]:
        total_requests = self.stats["total_requests"]
        hit_rate = (self.stats["hits"] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "cache_hits": self.stats["hits"],
            "cache_misses": self.stats["misses"],
            "total_requests": total_requests,
            "hit_rate_percentage": round(hit_rate, 2),
            "cache_size": len(self.cache),
            "max_cache_size": self.cache.maxsize,
            "ttl_seconds": self.ttl_seconds,
            "current_time": datetime.now().isoformat()
        }
    
    def get_cache_info(self) -> Dict[str, Any]:
        cache_entries = []
        current_time = datetime.now()
        
        for key, value in self.cache.items():
            if isinstance(value, dict) and "cache_info" in value:
                cache_info = value["cache_info"]
                expires_at = datetime.fromisoformat(cache_info["expires_at"])
                time_remaining = max(0, (expires_at - current_time).total_seconds())
                
                cache_entries.append({
                    "key": key,
                    "cached_at": cache_info["cached_at"],
                    "expires_at": cache_info["expires_at"],
                    "time_remaining_seconds": round(time_remaining, 2),
                    "total_noticias": value.get("total_noticias", "unknown")
                })
        
        return {
            "total_entries": len(cache_entries),
            "entries": cache_entries
        }
    
    def clear_cache(self) -> Dict[str, Any]:
        entries_before = len(self.cache)
        self.cache.clear()
        logger.info("Cache limpo manualmente")
        
        return {
            "message": "Cache limpo com sucesso",
            "entries_removed": entries_before,
            "cache_size_after": len(self.cache),
            "cleared_at": datetime.now().isoformat()
        }

news_cache = NewsCache(max_size=50, ttl_seconds=900)

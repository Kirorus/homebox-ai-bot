import aiohttp
import asyncio
import logging
from typing import List, Dict, Optional
import config
from utils import retry_async

logger = logging.getLogger(__name__)

class HomeboxAPI:
    def __init__(self):
        # Normalize base URL (strip trailing slash)
        self.base_url = (config.HOMEBOX_URL or "").rstrip("/")
        self.token = config.HOMEBOX_TOKEN
        self.username = config.HOMEBOX_USER
        self.password = config.HOMEBOX_PASSWORD
        self.last_error: Optional[str] = None
        self.headers = {
            'Authorization': self._build_auth_header(self.token),
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        self._session: Optional[aiohttp.ClientSession] = None
        self._session_lock = asyncio.Lock()

    def _build_auth_header(self, token: Optional[str]) -> str:
        """Собирает значение заголовка Authorization.
        Некоторые инсталляции Homebox ожидают чистый токен без префикса Bearer.
        Если в токене уже есть префикс 'Bearer ', используем как есть; иначе — передаём токен как есть без префикса.
        """
        if not token:
            return ''
        
        if token.startswith('Bearer '):
            return token
        else:
            return f'Bearer {token}'

    async def _get_session(self) -> aiohttp.ClientSession:
        """Получить или создать HTTP сессию"""
        async with self._session_lock:
            if self._session is None or self._session.closed:
                connector = aiohttp.TCPConnector(limit=100, limit_per_host=30)
                timeout = aiohttp.ClientTimeout(total=30, connect=10)
                self._session = aiohttp.ClientSession(
                    connector=connector,
                    timeout=timeout
                )
            return self._session

    async def close_session(self):
        """Закрыть HTTP сессию"""
        async with self._session_lock:
            if self._session and not self._session.closed:
                await self._session.close()
                self._session = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close_session()

    @retry_async(max_attempts=3, delay=2.0, exceptions=(aiohttp.ClientError, asyncio.TimeoutError))
    async def get_locations(self) -> List[Dict]:
        """Fetch all locations (boxes)."""
        try:
            await self.ensure_authorized()
            session = await self._get_session()
            
            logger.info("Fetching locations from HomeBox")
            
            async with session.get(
                f'{self.base_url}/api/v1/locations',
                headers=self.headers
            ) as response:
                if response.status != 200:
                    try:
                        body = await response.text()
                    except Exception:
                        body = ''
                    self.last_error = f'GET locations failed HTTP {response.status}; body: {body[:500]}'
                    logger.error(f"Failed to fetch locations: {self.last_error}")
                    return []
                
                try:
                    locations = await response.json()
                    logger.info(f"Successfully fetched {len(locations)} locations")
                    return locations
                except aiohttp.ContentTypeError as e:
                    self.last_error = f'GET locations response not JSON: {e}'
                    logger.error(self.last_error)
                    return []
                    
        except Exception as e:
            error_msg = f'Exception in get_locations: {str(e)}'
            logger.error(error_msg)
            return []

    @retry_async(max_attempts=3, delay=2.0, exceptions=(aiohttp.ClientError, asyncio.TimeoutError))
    async def create_item(
        self,
        name: str,
        description: str,
        location_id: str,
        photo_path: Optional[str] = None
    ) -> Dict:
        """Create a new item in HomeBox."""
        try:
            await self.ensure_authorized()
            session = await self._get_session()
            
            logger.info(f"Creating item: {name} in location {location_id}")
            
            # Prepare item data
            item_data = {
                'name': name,
                'description': description,
                'locationId': location_id,
                'quantity': 1
            }
            
            async with session.post(
                f'{self.base_url}/api/v1/items',
                headers=self.headers,
                json=item_data
            ) as response:
                if response.status != 201:
                    try:
                        body = await response.text()
                    except Exception:
                        body = ''
                    self.last_error = f'CREATE item failed HTTP {response.status}; body: {body[:500]}'
                    logger.error(f"Failed to create item: {self.last_error}")
                    return {'error': f'Failed to create item: HTTP {response.status}'}
                
                try:
                    item = await response.json()
                except aiohttp.ContentTypeError as e:
                    self.last_error = f'CREATE item response not JSON: {e}'
                    logger.error(self.last_error)
                    return {'error': 'Failed to parse item response'}
                
                item_id = item.get('id')
                logger.info(f"Successfully created item with ID: {item_id}")
                
                # If there's a photo, upload it
                if photo_path and item_id:
                    logger.info(f"Uploading photo for item {item_id}")
                    uploaded = await self.upload_photo(item_id, photo_path)
                    if not uploaded:
                        # Return flag/message so bot can show user
                        item['photo_upload'] = 'failed'
                        logger.warning(f"Photo upload failed for item {item_id}: {self.last_error}")
                    else:
                        logger.info(f"Photo upload succeeded for item {item_id}")
                
                return item
                
        except Exception as e:
            error_msg = f'Exception in create_item: {str(e)}'
            logger.error(error_msg)
            return {'error': 'Exception occurred', 'details': str(e)}
    
    async def upload_photo(self, item_id: str, photo_path: str) -> bool:
        """Загрузка через raw HTTP запрос для максимальной совместимости."""
        try:
            import os
            import uuid
            
            # Read file
            with open(photo_path, 'rb') as file:
                file_content = file.read()
            
            filename = os.path.basename(photo_path) or 'photo.jpg'
            
            logger.info(f"Uploading photo {filename} for item {item_id}")
            
            # Create boundary
            boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
            
            # Form request body manually
            body_parts = []
            
            # Add name field (required by API)
            body_parts.append(f'--{boundary}'.encode())
            body_parts.append(f'Content-Disposition: form-data; name="name"'.encode())
            body_parts.append(b'')
            body_parts.append(filename.encode())
            
            # Add file
            body_parts.append(f'--{boundary}'.encode())
            body_parts.append(f'Content-Disposition: form-data; name="file"; filename="{filename}"'.encode())
            body_parts.append(b'Content-Type: image/jpeg')
            body_parts.append(b'')
            body_parts.append(file_content)
            body_parts.append(f'--{boundary}--'.encode())
            
            body = b'\r\n'.join(body_parts)
            
            # Headers
            headers = {
                'Authorization': self._build_auth_header(self.token),
                'Content-Type': f'multipart/form-data; boundary={boundary}',
                'Content-Length': str(len(body))
            }
            
            # Send via aiohttp
            session = await self._get_session()
            async with session.post(
                f'{self.base_url}/api/v1/items/{item_id}/attachments',
                headers=headers,
                data=body
            ) as response:
                logger.debug(f"Upload response status: {response.status}")
                
                if response.status != 201:
                    try:
                        body_text = await response.text()
                    except Exception:
                        body_text = ''
                    self.last_error = f'Upload failed HTTP {response.status}; body: {body_text[:500]}'
                    logger.error(f"Photo upload failed: {self.last_error}")
                    return False
                
                logger.info(f"Successfully uploaded photo for item {item_id}")
                return True
                
        except Exception as e:
            self.last_error = f'Exception in upload_photo: {str(e)}'
            logger.error(f"Exception in upload_photo: {e}")
            return False

    async def ensure_authorized(self) -> None:
        """Ensure we have a valid token; if absent, perform login."""
        if self.token:
            # Token already exists
            return
            
        # Require username/password for login
        if not self.username or not self.password:
            self.last_error = 'No HOMEBOX_TOKEN and no HOMEBOX_USER/HOMEBOX_PASSWORD provided'
            logger.error(self.last_error)
            return
            
        try:
            # Perform login
            session = await self._get_session()
            
            login_headers = {
                'accept': 'application/json',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            payload = {
                'username': self.username,
                'password': self.password
            }
            
            logger.info("Attempting to login to HomeBox")
            
            async with session.post(
                f'{self.base_url}/api/v1/users/login',
                data=payload,
                headers=login_headers
            ) as response:
                if response.status != 200:
                    try:
                        body = await response.text()
                    except Exception:
                        body = ''
                    self.last_error = f'LOGIN failed HTTP {response.status}; body: {body[:500]}'
                    logger.error(f"Login failed: {self.last_error}")
                    return
                    
                try:
                    data = await response.json()
                except aiohttp.ContentTypeError as e:
                    self.last_error = f'LOGIN response not JSON: {e}'
                    logger.error(self.last_error)
                    return
                    
                token = data.get('token')
                if not token:
                    self.last_error = 'LOGIN response missing token'
                    logger.error(self.last_error)
                    return
                    
                self.token = token
                self.headers['Authorization'] = self._build_auth_header(token)
                logger.info("Successfully logged in to HomeBox")
                
        except Exception as e:
            self.last_error = f'Exception during login: {str(e)}'
            logger.error(self.last_error)

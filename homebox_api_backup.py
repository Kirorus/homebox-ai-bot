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
        if isinstance(token, str) and token.strip().lower().startswith('bearer '):
            return token
        return token
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Получить или создать HTTP сессию"""
        async with self._session_lock:
            if self._session is None or self._session.closed:
                timeout = aiohttp.ClientTimeout(total=30, connect=10)
                connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
                self._session = aiohttp.ClientSession(
                    timeout=timeout,
                    connector=connector,
                    headers=self.headers
                )
                logger.info("Created new HTTP session")
            return self._session
    
    async def close_session(self):
        """Закрыть HTTP сессию"""
        async with self._session_lock:
            if self._session and not self._session.closed:
                await self._session.close()
                logger.info("Closed HTTP session")
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close_session()
    
    @retry_async(max_attempts=3, delay=1.0, exceptions=(aiohttp.ClientError, asyncio.TimeoutError))
    async def get_locations(self) -> List[Dict]:
        """Fetch all locations (boxes)."""
        try:
        await self.ensure_authorized()
            session = await self._get_session()
            
            async with session.get(f'{self.base_url}/api/v1/locations') as response:
                if response.status != 200:
                    # Try read error body for diagnostics
                    try:
                        error_text = await response.text()
                    except Exception:
                        error_text = ''
                    self.last_error = f'GET /api/v1/locations -> HTTP {response.status}; body: {error_text[:500]}'
                    logger.error(f"Failed to get locations: {self.last_error}")
                    return []
                
                # Safe JSON parse: proxies/redirects may return HTML
                try:
                    data = await response.json()
                except aiohttp.ContentTypeError as e:
                    self.last_error = f'GET /api/v1/locations -> invalid content-type (expected JSON): {e}'
                    logger.error(self.last_error)
                    return []
                
                # Support both array response and object { items: [] }
                locations: List[Dict] = []
                if isinstance(data, list):
                    locations = data
                elif isinstance(data, dict):
                    items = data.get('items')
                    if isinstance(items, list):
                        locations = items
                
                self.last_error = None
                logger.info(f"Successfully fetched {len(locations)} locations")
                return locations
                
        except Exception as e:
            self.last_error = f'Exception in get_locations: {str(e)}'
            logger.error(f"Exception in get_locations: {e}")
            return []
    
    @retry_async(max_attempts=2, delay=1.0, exceptions=(aiohttp.ClientError, asyncio.TimeoutError))
    async def create_item(
        self,
        name: str,
        description: str,
        location_id: str,
        photo_path: Optional[str] = None
    ) -> Dict:
        """Create a new item in HomeBox."""
        try:
        # Сначала создаем предмет
        await self.ensure_authorized()
            session = await self._get_session()
            
        item_data = {
            'name': name,
            'description': description,
            'locationId': location_id,
            'quantity': 1
        }
        
            logger.info(f"Creating item: {name} in location {location_id}")
            
            async with session.post(
                f'{self.base_url}/api/v1/items',
                json=item_data
            ) as response:
                if response.status != 201:
                    try:
                        error_text = await response.text()
                    except Exception:
                        error_text = ''
                    error_msg = f'Failed to create item: HTTP {response.status}; {error_text}'
                    logger.error(error_msg)
                    return {'error': 'Failed to create item', 'details': error_text}

                try:
                    item = await response.json()
                except aiohttp.ContentTypeError as e:
                    error_msg = f'Failed to parse item response: {e}'
                    logger.error(error_msg)
                    return {'error': 'Failed to parse item response'}
                
                item_id = item.get('id')
                logger.info(f"Successfully created item with ID: {item_id}")
                
                # Если есть фото, загружаем его
                if photo_path and item_id:
                    logger.info(f"Uploading photo for item {item_id}")
                    uploaded = await self.upload_photo(item_id, photo_path)
                    if not uploaded:
                        # Вернём флаг/сообщение, чтобы бот мог показать пользователю
                        item['photo_upload'] = 'failed'
                        logger.warning(f"Photo upload failed for item {item_id}: {self.last_error}")
                    else:
                        logger.info(f"Photo upload succeeded for item {item_id}")
                
                return item
    
        except Exception as e:
            error_msg = f'Exception in create_item: {str(e)}'
            logger.error(error_msg)
            return {'error': 'Exception occurred', 'details': str(e)}
    
    @retry_async(max_attempts=3, delay=2.0, exceptions=(aiohttp.ClientError, asyncio.TimeoutError))
    async def upload_photo(self, item_id: str, photo_path: str) -> bool:
        """Upload a photo for the given item."""
        try:
            session = await self._get_session()
            
            # Читаем файл в память для лучшего контроля
            with open(photo_path, 'rb') as file:
                file_content = file.read()
            
            # Определяем тип файла по расширению
                import os as _os
            import mimetypes
                filename = _os.path.basename(photo_path) or 'photo.jpg'
            mime_type, _ = mimetypes.guess_type(photo_path)
            if not mime_type or not mime_type.startswith('image/'):
                mime_type = 'image/jpeg'
            
            logger.info(f"Uploading photo {filename} (type: {mime_type}) for item {item_id}")
            
            # Создаем FormData с правильным форматом
            data = aiohttp.FormData()
            
            # Пробуем разные варианты добавления файла в зависимости от API
            # Вариант 1: Стандартный способ
            data.add_field(
                'file',
                file_content,
                filename=filename,
                content_type=mime_type
            )
            
            # API требует поле 'name'
                data.add_field('name', filename)
            
            # Создаем заголовки без Content-Type (aiohttp установит его автоматически)
            upload_headers = {
                'Authorization': self._build_auth_header(self.token)
            }
            
            # Логируем детали запроса для отладки
            logger.debug(f"Upload URL: {self.base_url}/api/v1/items/{item_id}/attachments")
            logger.debug(f"Headers: {upload_headers}")
            logger.debug(f"File size: {len(file_content)} bytes")
            
            async with session.post(
                f'{self.base_url}/api/v1/items/{item_id}/attachments',
                headers=upload_headers,
                data=data
            ) as response:
                logger.debug(f"Upload response status: {response.status}")
                logger.debug(f"Upload response headers: {dict(response.headers)}")
                
                if response.status != 201:
                    try:
                        body = await response.text()
                        logger.debug(f"Upload error response body: {body}")
                    except Exception:
                        body = ''
                    self.last_error = f'UPLOAD photo failed HTTP {response.status}; body: {body[:500]}'
                    logger.error(f"Photo upload failed: {self.last_error}")
                    return False
                
                try:
                    response_data = await response.json()
                    logger.info(f"Successfully uploaded photo for item {item_id}, response: {response_data}")
                except Exception:
                    logger.info(f"Successfully uploaded photo for item {item_id}")
                
                return True
                    
        except Exception as e:
            self.last_error = f'Exception in upload_photo: {str(e)}'
            logger.error(f"Exception in upload_photo: {e}")
            return False
    
    async def upload_photo_alternative(self, item_id: str, photo_path: str) -> bool:
        """Alternative photo upload method for problematic APIs."""
        try:
            session = await self._get_session()
            
            # Читаем файл
            with open(photo_path, 'rb') as file:
                file_content = file.read()
            
            import os as _os
            filename = _os.path.basename(photo_path) or 'photo.jpg'
            
            logger.info(f"Trying alternative upload for {filename} to item {item_id}")
            
            # Создаем простой FormData с обязательным полем name
            data = aiohttp.FormData()
            data.add_field('file', file_content, filename=filename)
            data.add_field('name', filename)
            
            upload_headers = {
                'Authorization': self._build_auth_header(self.token)
            }
                
                async with session.post(
                    f'{self.base_url}/api/v1/items/{item_id}/attachments',
                headers=upload_headers,
                    data=data
                ) as response:
                    if response.status != 201:
                        try:
                            body = await response.text()
                        except Exception:
                            body = ''
                    self.last_error = f'Alternative upload failed HTTP {response.status}; body: {body[:500]}'
                    logger.error(f"Alternative photo upload failed: {self.last_error}")
                    return False
                
                logger.info(f"Successfully uploaded photo using alternative method for item {item_id}")
                return True
                
        except Exception as e:
            self.last_error = f'Exception in alternative upload_photo: {str(e)}'
            logger.error(f"Exception in alternative upload_photo: {e}")
            return False
    
    async def upload_photo_base64(self, item_id: str, photo_path: str) -> bool:
        """Upload photo as base64 JSON (alternative method)."""
        try:
            session = await self._get_session()
            
            # Читаем файл и конвертируем в base64
            with open(photo_path, 'rb') as file:
                file_content = file.read()
            
            import base64
            import os as _os
            
            filename = _os.path.basename(photo_path) or 'photo.jpg'
            base64_content = base64.b64encode(file_content).decode('utf-8')
            
            logger.info(f"Trying base64 upload for {filename} to item {item_id}")
            
            # Создаем JSON payload
            payload = {
                'name': filename,
                'file': base64_content,
                'mimeType': 'image/jpeg'
            }
            
            upload_headers = {
                'Authorization': self._build_auth_header(self.token),
                'Content-Type': 'application/json'
            }
            
            async with session.post(
                f'{self.base_url}/api/v1/items/{item_id}/attachments',
                headers=upload_headers,
                json=payload
            ) as response:
                if response.status != 201:
                    try:
                        body = await response.text()
                    except Exception:
                        body = ''
                    self.last_error = f'Base64 upload failed HTTP {response.status}; body: {body[:500]}'
                    logger.error(f"Base64 photo upload failed: {self.last_error}")
                    return False
                
                logger.info(f"Successfully uploaded photo using base64 method for item {item_id}")
                return True
                
        except Exception as e:
            self.last_error = f'Exception in base64 upload_photo: {str(e)}'
            logger.error(f"Exception in base64 upload_photo: {e}")
            return False
    
    async def upload_photo_curl_style(self, item_id: str, photo_path: str) -> bool:
        """Загрузка в стиле curl с правильными заголовками."""
        try:
            session = await self._get_session()
            
            # Читаем файл
            with open(photo_path, 'rb') as file:
                file_content = file.read()
            
            import os as _os
            filename = _os.path.basename(photo_path) or 'photo.jpg'
            
            logger.info(f"Trying curl-style upload for {filename} to item {item_id}")
            
            # Создаем FormData с обязательным полем name
            data = aiohttp.FormData()
            data.add_field(
                'file', 
                file_content, 
                filename=filename
                # Не указываем content_type - пусть aiohttp определит сам
            )
            data.add_field('name', filename)
            
            # Минимальные заголовки
            upload_headers = {
                'Authorization': self._build_auth_header(self.token)
                # Content-Type будет установлен автоматически
            }
            
            async with session.post(
                f'{self.base_url}/api/v1/items/{item_id}/attachments',
                headers=upload_headers,
                data=data
            ) as response:
                logger.debug(f"Curl-style upload response status: {response.status}")
                
                if response.status != 201:
                    try:
                        body = await response.text()
                    except Exception:
                        body = ''
                    self.last_error = f'Curl-style upload failed HTTP {response.status}; body: {body[:500]}'
                    logger.error(f"Curl-style photo upload failed: {self.last_error}")
                    return False
                
                logger.info(f"Successfully uploaded photo using curl-style method for item {item_id}")
                return True
                
        except Exception as e:
            self.last_error = f'Exception in curl-style upload: {str(e)}'
            logger.error(f"Exception in curl-style upload: {e}")
            return False
    
    async def upload_photo(self, item_id: str, photo_path: str) -> bool:
        """Загрузка через raw HTTP запрос для максимальной совместимости."""
        try:
            import os
            import uuid
            
            # Читаем файл
            with open(photo_path, 'rb') as file:
                file_content = file.read()
            
            filename = os.path.basename(photo_path) or 'photo.jpg'
            
            logger.info(f"Trying raw HTTP upload for {filename} to item {item_id}")
            
            # Создаем boundary
            boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
            
            # Формируем тело запроса вручную
            body_parts = []
            
            # Добавляем поле name (требуется API)
            body_parts.append(f'--{boundary}'.encode())
            body_parts.append(f'Content-Disposition: form-data; name="name"'.encode())
            body_parts.append(b'')
            body_parts.append(filename.encode())
            
            # Добавляем файл
            body_parts.append(f'--{boundary}'.encode())
            body_parts.append(f'Content-Disposition: form-data; name="file"; filename="{filename}"'.encode())
            body_parts.append(b'Content-Type: image/jpeg')
            body_parts.append(b'')
            body_parts.append(file_content)
            body_parts.append(f'--{boundary}--'.encode())
            
            body = b'\r\n'.join(body_parts)
            
            # Заголовки
            headers = {
                'Authorization': self._build_auth_header(self.token),
                'Content-Type': f'multipart/form-data; boundary={boundary}',
                'Content-Length': str(len(body))
            }
            
            # Отправляем через aiohttp
            session = await self._get_session()
            async with session.post(
                f'{self.base_url}/api/v1/items/{item_id}/attachments',
                headers=headers,
                data=body
            ) as response:
                logger.debug(f"Raw HTTP upload response status: {response.status}")
                
                if response.status != 201:
                    try:
                        body_text = await response.text()
                    except Exception:
                        body_text = ''
                    self.last_error = f'Raw HTTP upload failed HTTP {response.status}; body: {body_text[:500]}'
                    logger.error(f"Raw HTTP photo upload failed: {self.last_error}")
                    return False
                
                logger.info(f"Successfully uploaded photo using raw HTTP method for item {item_id}")
                return True
                
        except Exception as e:
            self.last_error = f'Exception in raw HTTP upload: {str(e)}'
            logger.error(f"Exception in raw HTTP upload: {e}")
            return False

    async def check_api_capabilities(self) -> dict:
        """Проверяет возможности API HomeBox для загрузки файлов."""
        try:
            await self.ensure_authorized()
            session = await self._get_session()
            
            # Проверяем различные endpoints для понимания API
            endpoints_to_check = [
                f'{self.base_url}/api/v1',
                f'{self.base_url}/api/v1/attachments',
                f'{self.base_url}/api/v1/items',
                f'{self.base_url}/docs',
                f'{self.base_url}/swagger.json',
                f'{self.base_url}/openapi.json'
            ]
            
            results = {}
            for endpoint in endpoints_to_check:
                try:
                    async with session.get(endpoint) as response:
                        if response.status == 200:
                            try:
                                content_type = response.headers.get('content-type', '')
                                if 'application/json' in content_type:
                                    data = await response.json()
                                    results[endpoint] = {'status': response.status, 'data': data}
                                else:
                                    results[endpoint] = {'status': response.status, 'content_type': content_type}
                                logger.info(f"Endpoint {endpoint} available: {response.status}")
                            except Exception as e:
                                results[endpoint] = {'status': response.status, 'error': str(e)}
                        else:
                            results[endpoint] = {'status': response.status}
                except Exception as e:
                    results[endpoint] = {'error': str(e)}
            
            return results
            
        except Exception as e:
            logger.warning(f"Could not check API capabilities: {e}")
            return {}
    
    async def try_different_endpoints(self, item_id: str, photo_path: str) -> dict:
        """Пробует загрузить файл на разные endpoints."""
        endpoints = [
            f'/api/v1/items/{item_id}/attachments',
            f'/api/v1/items/{item_id}/files',
            f'/api/v1/items/{item_id}/photos',
            f'/api/v1/items/{item_id}/images',
            f'/api/v1/attachments',
            f'/api/v1/files',
            f'/api/v1/upload'
        ]
        
        results = {}
        for endpoint in endpoints:
            try:
                result = await self.upload_photo_to_endpoint(endpoint, photo_path)
                results[endpoint] = result
                if result:
                    logger.info(f"Successfully uploaded to endpoint: {endpoint}")
                    break
            except Exception as e:
                results[endpoint] = {'error': str(e)}
        
        return results
    
    async def upload_photo_to_endpoint(self, endpoint: str, photo_path: str) -> bool:
        """Загружает фото на конкретный endpoint."""
        try:
            session = await self._get_session()
            
            with open(photo_path, 'rb') as file:
                file_content = file.read()
            
            import os
            filename = os.path.basename(photo_path) or 'photo.jpg'
            
            # Простой multipart запрос с обязательным полем name
            data = aiohttp.FormData()
            data.add_field('file', file_content, filename=filename)
            data.add_field('name', filename)
            
            headers = {
                'Authorization': self._build_auth_header(self.token)
            }
            
            async with session.post(
                f'{self.base_url}{endpoint}',
                headers=headers,
                data=data
            ) as response:
                if response.status == 201:
                    logger.info(f"Upload successful to {endpoint}")
                    return True
                else:
                    logger.debug(f"Upload failed to {endpoint}: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error uploading to {endpoint}: {e}")
                        return False
    
    async def upload_photo_different_fields(self, item_id: str, photo_path: str) -> dict:
        """Пробует загрузить файл с разными именами полей."""
        field_names = ['file', 'image', 'photo', 'attachment', 'upload', 'data']
        results = {}
        
        for field_name in field_names:
            try:
                result = await self.upload_photo_with_field(item_id, photo_path, field_name)
                results[field_name] = result
                if result:
                    logger.info(f"Successfully uploaded with field name: {field_name}")
                    break
            except Exception as e:
                results[field_name] = {'error': str(e)}
        
        return results
    
    async def upload_photo_with_field(self, item_id: str, photo_path: str, field_name: str) -> bool:
        """Загружает фото с указанным именем поля."""
        try:
            session = await self._get_session()
            
            with open(photo_path, 'rb') as file:
                file_content = file.read()
            
            import os
            filename = os.path.basename(photo_path) or 'photo.jpg'
            
            # Создаем FormData с указанным именем поля и обязательным полем name
            data = aiohttp.FormData()
            data.add_field(field_name, file_content, filename=filename)
            data.add_field('name', filename)
            
            headers = {
                'Authorization': self._build_auth_header(self.token)
            }
            
            async with session.post(
                f'{self.base_url}/api/v1/items/{item_id}/attachments',
                headers=headers,
                data=data
            ) as response:
                if response.status == 201:
                    logger.info(f"Upload successful with field '{field_name}'")
                    return True
                else:
                    logger.debug(f"Upload failed with field '{field_name}': {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error uploading with field '{field_name}': {e}")
            return False
    
    async def test_upload_methods(self, item_id: str, photo_path: str) -> dict:
        """Тестирует разные методы загрузки и возвращает результаты."""
        results = {}
        
        # Тест 1: Стандартный multipart
        try:
            result = await self.upload_photo(item_id, photo_path)
            results['standard_multipart'] = result
        except Exception as e:
            results['standard_multipart'] = False
            results['standard_multipart_error'] = str(e)
        
        # Тест 2: Альтернативный multipart
        try:
            result = await self.upload_photo_alternative(item_id, photo_path)
            results['alternative_multipart'] = result
        except Exception as e:
            results['alternative_multipart'] = False
            results['alternative_multipart_error'] = str(e)
        
        # Тест 3: Base64 JSON
        try:
            result = await self.upload_photo_base64(item_id, photo_path)
            results['base64_json'] = result
        except Exception as e:
            results['base64_json'] = False
            results['base64_json_error'] = str(e)
        
        # Тест 4: Curl-style
        try:
            result = await self.upload_photo_curl_style(item_id, photo_path)
            results['curl_style'] = result
        except Exception as e:
            results['curl_style'] = False
            results['curl_style_error'] = str(e)
        
        # Тест 5: Raw HTTP
        try:
            result = await self.upload_photo_raw_http(item_id, photo_path)
            results['raw_http'] = result
        except Exception as e:
            results['raw_http'] = False
            results['raw_http_error'] = str(e)
        
        logger.info(f"Upload test results for item {item_id}: {results}")
        return results

    async def ensure_authorized(self) -> None:
        """Ensure we have a valid token; if absent, perform login."""
        if self.token:
            # Токен уже есть
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
                    
                # В некоторых установках нужен чистый токен без Bearer — используем стратегию _build_auth_header
                self.token = token
                self.headers['Authorization'] = self._build_auth_header(self.token)
                self.last_error = None
                logger.info("Successfully logged in to HomeBox")
                
        except Exception as e:
            self.last_error = f'Exception in ensure_authorized: {str(e)}'
            logger.error(f"Exception in ensure_authorized: {e}")

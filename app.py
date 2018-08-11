import websockets
import asyncio
import json
import time, os


class HttpWSSProtocol(websockets.WebSocketServerProtocol):
    rwebsocket = None
    rddata = None
    async def handler(self):
        try:
            request_line, headers = await websockets.http.read_message(self.reader)
            method, path, version = request_line[:-2].decode().split(None, 2)
            #websockets.accept()
        except Exception as e:
            print(e.args)
            self.writer.close()
            self.ws_server.unregister(self)

            raise

        # TODO: Check headers etc. to see if we are to upgrade to WS.
        if path == '/ws':
            # HACK: Put the read data back, to continue with normal WS handling.
            self.reader.feed_data(bytes(request_line))
            self.reader.feed_data(headers.as_bytes().replace(b'\n', b'\r\n'))

            return await super(HttpWSSProtocol, self).handler()
        else:
            try:
                return await self.http_handler(method, path, version)
            except Exception as e:
                print(e)
            finally:

                self.writer.close()
                self.ws_server.unregister(self)


    async def http_handler(self, method, path, version):
        response = ''
        try:

            googleRequest = self.reader._buffer.decode('utf-8')
            googleRequestJson = json.loads(googleRequest)

            #{"location": "living", "state": "on", "device": "rele1"}
            if 'cómo' in googleRequestJson['result']['resolvedQuery']:
                ESPparameters = googleRequestJson['result']['parameters']
                ESPparameters['query'] = '?' # Sergio si query = ?  entramos en comandos para consultar estado de reles
            else:
                ESPparameters = googleRequestJson['result']['parameters']
                ESPparameters['query'] = 'cmd'  # Sergio si query = cmd  entramos en comandos para des-activar reles
            # send command to ESP over websocket
            if self.rwebsocket== None:
                print("Device is not connected!")
                return
            await self.rwebsocket.send(json.dumps(ESPparameters))

            #wait for response and send it back to API.ai as is
            self.rddata = await self.rwebsocket.recv()
            #{"speech": "It is working", "displayText": "It is working"}
            print(self.rddata)
            state = json.loads(self.rddata)['state']
            #Sergio Original {self.rddata = '{"speech": "Sistema '+state+'", "displayText": "Sistema '+state+'"}'
            #Sergio modificaciones realizadas por mi para probar y depurar
            if ESPparameters['query'] == '?' :
                print("Entra en if de consulta estado de reles")
                if ESPparameters['device'] == 'rele1' :
                    print("Consulta Rele1 detectado")
                    self.rddata = '{"speech": "Rele1 esta en '+state+'", "displayText": "Rele1 esta en '+state+'"}'
                else: 
                    print("else Rele1 No detectado")
                    self.rddata = '{"speech": "Esta en '+state+'", "displayText": "Esta en '+state+'"}'
            else: 
                print("Entra en else de activar o desactivar los reles")
                if ESPparameters['device'] == 'rele1' :
                    print("Rele1 detectado")
                    self.rddata = '{"speech": "Relé 1 '+state+'", "displayText": "Rele 1 '+state+'"}'
                else: 
                    print("else Rele1 No detectado")
                    self.rddata = '{"speech": "Relé '+state+'", "displayText": "Rele '+state+'"}'
            response = '\r\n'.join([
                'HTTP/1.1 200 OK',
                'Content-Type: text/json',
                '',
                ''+self.rddata+'',
            ])
        except Exception as e:
            print(e)
        self.writer.write(response.encode())

def updateData(data):
    HttpWSSProtocol.rddata = data

async def ws_handler(websocket, path):
    game_name = 'g1'
    try:
        HttpWSSProtocol.rwebsocket = websocket
        await websocket.send(json.dumps({'event': 'OK'}))
        data ='{"empty":"empty"}'
        while True:
            data = await websocket.recv()
            updateData(data)
    except Exception as e:
        print(e)
    finally:
        print("")



port = int(os.getenv('PORT', 5687))
start_server = websockets.serve(ws_handler, '', port, klass=HttpWSSProtocol)
# logger.info('Listening on port %d', port)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()

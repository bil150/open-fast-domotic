# open-fast-domotic: API collection (Bruno)

Open this folder in [Bruno](https://www.usebruno.com) (Open Collection) and select the **local** environment.

- `baseUrl` is the API of the server started with `npm run dev` (http://localhost:8000/api/v1).
- `deviceId`, `sceneId`, `zoneId`... are the identifiers the requests use: take them from the answers of the
  list requests and change them in the environment. `buttonId` is a button or a remote.
- The WebSockets (`/api/v1/ws` live events, `/api/v1/stream` fast colors) are not in this collection.
- The interactive documentation of the server is on http://localhost:8000/docs.

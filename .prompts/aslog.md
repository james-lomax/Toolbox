{{template("new-tool.md", tool_name="aslog")}}

`aslog` is a tool for converting Android Studio log files to a simpler JSON format.

Usage: `aslog file.json [output_file] [--via-only]`

Android Studio log files look like this:


```json
[
  {
    "duration-microseconds": 254863,
    "method": "POST",
    "request-content-type": "",
    "request-headers": {
      "Accept-Encoding": "gzip",
      "User-Agent": "Via/4.24.1/app_cICCSChpsdqvkql23BFYgBMoXbnnCJRGHEag44qT9bo/android/7.0.1/Android OS/14/gzip/s"
    },
    "request-payload-base64": "ZGF0YT0lN0...",
    "response-code": 200,
    "response-content-type": "application/json",
    "response-headers": {
      "access-control-allow-origin": "*",
      "Alt-Svc": "h3\u003d\":443\"; ma\u003d2592000,h3-29\u003d\":443\"; ma\u003d2592000",
      "content-encoding": "gzip",
      "content-type": "application/json;charset\u003dutf-8",
      "date": "Thu, 06 Nov 2025 15:28:50 GMT",
      "null": "HTTP/1.1 200 OK",
      "server": "istio-envoy",
      "Transfer-Encoding": "chunked",
      "vary": "Accept-Encoding",
      "Via": "1.1 google",
      "X-Android-Received-Millis": "1762442927004",
      "X-Android-Response-Source": "NETWORK 200",
      "X-Android-Selected-Protocol": "http/1.1",
      "X-Android-Sent-Millis": "1762442926760",
      "x-envoy-upstream-service-time": "135"
    },
    "response-payload-base64": "eyJyZXNwb2...",
    "url": "https://api.leanplum.com/api"
  },
  ...
]
```

Request and response are base64 encoded, sometimes the contents is gzipped as well.

aslog simplifies these logs into a list of objects like this:

```json
[
    {
        "duration-secs": 0.25, // 2 significant figures
        "method": "POST",
        "url": "https://api.leanplum.com/api",
        "request-body": {
            ... // If possible, decode the request body to JSON, otherwise request-body is null
        },
        "response-time": "2025-11-06T152850Z", // ISO8601 formatted
        "response-status": 200,
        "response-body": {
            ... // If possible, decode the request body to JSON, otherwise response-body is null
        }
    },
    ...
]
```

This is a tool for inspecting REST APIs so we expect all the requests we care about to have JSON encoded requests/responses. As such we only include request/response body if it can be decoded as JSON, and we include it as a JSON object rather than the string of JSON data.

To decode it, first decode the base64 to bytes, then try and decode this as a JSON string, or if that doesn't work try un-gzipping it, and then decoding. If neither works, just store null.

If an output_file is specified, this is used to store the output, otherwise we derive the output file name from the input file, so if the input file is `example.json`, the output is `example.simple.json`.

If `--via-only` is specified, we filter to only include requests to hosts that end with `.ridewithvia.com` (use a regex on the URL to check this).

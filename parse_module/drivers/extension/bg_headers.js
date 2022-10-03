var addHeaders = %s;
var targetHeaders = [];
chrome.webRequest.onBeforeSendHeaders.addListener(
    function(details) {
        var headers = details.requestHeaders,
                blockingResponse = {};
        targetHeaders.splice(0, targetHeaders.length);
        for (var i = 0, l = headers.length; i < l; ++i) {
            var sourceHeader = headers[i];
            targetHeaders.push({name: sourceHeader.name, value: sourceHeader.value});
        }
        for (var i = 0, l = addHeaders.length; i < l; ++i) {
            var header = addHeaders[i];
            targetHeaders.push({name: header.name, value: header.value});
        }
        blockingResponse.requestHeaders = targetHeaders;
        return blockingResponse;
    },
    {urls: ['<all_urls>']},
    [ 'blocking', 'requestHeaders']
);

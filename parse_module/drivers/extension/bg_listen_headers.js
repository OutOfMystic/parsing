
var all_headers = new Map();
//var all_headers = [];
chrome.webRequest.onBeforeSendHeaders.addListener(
    function(details) {
        var headers = details.requestHeaders
        for (var i = 0, l = headers.length; i < l; ++i) {
            var sourceHeader = headers[i];
            if (sourceHeader.name != 'Cookie') {
                all_headers.set(sourceHeader.name, sourceHeader.value.replace(new RegExp('"','g'),"'''"));
                json_headers = JSON.stringify([...all_headers]);
                chrome.tabs.executeScript({code: "window.localStorage.setItem('headers', '" + json_headers + "');"});
            }
            //all_headers.push(sourceHeader.name + ': ' + sourceHeader.value);
            //alert(sourceHeader.name + ': ' + sourceHeader.value);
        }
        blockingResponse = {}
        blockingResponse.requestHeaders = details.requestHeaders;
        return blockingResponse;
    },
    {urls: ['<all_urls>']},
    [ 'blocking', 'requestHeaders']
);
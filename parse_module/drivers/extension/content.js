
var s = document.createElement('script');
s.src = chrome.extension.getURL('listen_response.js');
s.onload = function() {
    this.remove();
};
(document.head || document.documentElement).appendChild(s);

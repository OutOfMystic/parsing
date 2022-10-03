
var config = {
        mode: "fixed_servers",
        rules: {
          singleProxy: {
            scheme: "%s",
            host: "%s",
            port: parseInt(%s)
          },
          bypassList: ["localhost"]
        }
      };
chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});
chrome.webRequest.onAuthRequired.addListener(
            function callbackFn(details) {
                return {
                    authCredentials: {
                        username: "%s",
                        password: "%s"
                    }
                };
            },
            {urls: ["<all_urls>"]},
            ['blocking']
);
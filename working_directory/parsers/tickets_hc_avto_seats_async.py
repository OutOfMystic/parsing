test = await self.session.get(url = url_sector, headers=headers3)
            if test.headers['Content-Type'] == 'application/json':
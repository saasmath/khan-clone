from request_handler import RequestHandler

class CommonCore(RequestHandler):
    def post(self):
        self.get()

    def get(self):
        self.redirect("/api/v1/commoncore")
        return


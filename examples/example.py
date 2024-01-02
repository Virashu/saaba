from saaba import App, Request, Response

if __name__ == "__main__":
    app = App()

    @app.get("/api")
    def _(req: Request, res: Response):
        res.send('API<br><a href="/"><-</a>')
        res.add("<style>*{font-family:'Fira Code';}</style>")
        res.add(f"{req.path}")

    try:
        app.listen(
            "0.0.0.0", 8888, lambda: print("\x1b[34mhttp://127.0.0.1:8888/api\x1b[0m")
        )
    except KeyboardInterrupt:
        ...

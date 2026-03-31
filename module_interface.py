class LiteBotModuleInterface:
    """
    Base interface for LiteBot modules.
    """
    def fit(self, X=None, y=None):
        pass

    def predict(self, X):
        pass

    def score(self, X=None, y=None):
        return None

    def log_results(self, filename=None):
        pass

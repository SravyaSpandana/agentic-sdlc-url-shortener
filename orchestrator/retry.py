class RetryPolicy:
    """
    Controls bounded retries for workflow tasks.
    """

    def __init__(self, max_retries: int = 2):
        if max_retries < 0:
            raise ValueError(
                "max_retries cannot be negative"
            )

        self.max_retries = max_retries

    def can_retry(
        self,
        retry_count: int,
    ) -> bool:
        return retry_count < self.max_retries
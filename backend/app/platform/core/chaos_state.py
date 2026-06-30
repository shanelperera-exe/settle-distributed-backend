class ChaosState:
    def __init__(self):
        self.db_delay_seconds: float = 0.0
        self.db_error_rate: float = 0.0

# Global singleton instance
chaos_state = ChaosState()

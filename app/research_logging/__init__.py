from .research_logger import build_logger, ResearchLogger

RESEARCH_LOG_PATH = "/app/logs/research.log"

logger = build_logger(RESEARCH_LOG_PATH)
research_logger = ResearchLogger(logger)

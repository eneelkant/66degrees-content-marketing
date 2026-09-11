from typing import Dict, Type
from .base import BaseContentStrategy
from .blog_strategist import BlogStrategistStrategy
from .case_study_producer import CaseStudyProducerStrategy
from .copywriter import CopywriterStrategy
from .newsletter_curator import NewsletterCuratorStrategy
from .thought_leadership import ThoughtLeadershipStrategy
from .video_script import VideoScriptStrategy
from .website_writer import WebsiteWriterStrategy
from .whitepaper_architect import WhitepaperArchitectStrategy


class ContentStrategyFactory:
    def __init__(self):
        self._strategies: Dict[str, Type[BaseContentStrategy]] = {
            "blog": BlogStrategistStrategy,
            "case_study": CaseStudyProducerStrategy,
            "thought_leadership": ThoughtLeadershipStrategy,
            "website": WebsiteWriterStrategy,
            "newsletter": NewsletterCuratorStrategy,
            "whitepaper": WhitepaperArchitectStrategy,
            "video_script": VideoScriptStrategy,
            "copywriting": CopywriterStrategy,
        }

    def get_strategy(self, asset_type: str) -> BaseContentStrategy:
        asset_key = asset_type.lower().strip()
        if asset_key not in self._strategies:
            valid_types = ", ".join(self._strategies.keys())
            raise ValueError(f"Unsupported asset_type '{asset_type}'. Valid types are: {valid_types}")
        return self._strategies[asset_key]()

    def supported_types(self) -> tuple[str, ...]:
        return tuple(self._strategies.keys())


content_factory = ContentStrategyFactory()

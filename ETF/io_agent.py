import yaml
import time
import os
import asyncio
import base64
import shutil
from pathlib import Path
from typing import List, Optional
from driver.driver import InputAgent, OutputAgent
from openai import AsyncOpenAI

class TimingPromptAgent(InputAgent):
    
    def __init__(self, config_file="timing.yaml"):
        super().__init__()
        self.config_file = config_file
        self.timer = 0.0
        self.last_check_time = time.time()
        self.config_update_interval = 5.0  # Check config every 5 seconds
        self.last_config_check = time.time()
        
        # Load initial configuration
        self.load_configuration()
        
        self.logger.info(f"TimingPromptAgent initialized with config file: {self.config_file}")
        
    def load_configuration(self):
        """Load configuration from YAML file"""
        try:
            config_path = os.path.join(os.path.dirname(__file__), self.config_file)
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            self.trigger_time = float(config.get('time', 60))
            self.prompt_content = config.get('prompt', "")
            
            self.logger.info(f"Configuration loaded: trigger_time={self.trigger_time}s, prompt_length={len(self.prompt_content)} chars")
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration from {self.config_file}: {e}")
            # Set default values if config loading fails
            self.trigger_time = 60.0
            self.prompt_content = ""
    
    def seek_signal(self, message: str):
        """根据message决定是否进行seek"""
        # TimingPromptAgent doesn't need to seek based on messages
        pass
        
    def has_data_to_send(self) -> bool:
        """Check if timer has exceeded trigger time"""
        current_time = time.time()
        elapsed = current_time - self.last_check_time
        self.timer += elapsed
        self.last_check_time = current_time
        
        # Check if we should update configuration
        if current_time - self.last_config_check >= self.config_update_interval:
            self.load_configuration()
            self.last_config_check = current_time
        
        should_send = self.timer >= self.trigger_time
        if should_send:
            self.logger.debug(f"Timer reached {self.timer:.2f}s (trigger: {self.trigger_time}s), ready to send prompt")
        
        return should_send
        
    def collect_data(self) -> str:
        """Return the prompt content and reset timer"""
        self.logger.info(f"Sending prompt after {self.timer:.2f}s timer")
        data = self.prompt_content
        
        # Reset timer
        self.timer = 0.0
        self.last_check_time = time.time()
        
        self.logger.debug(f"Timer reset, prompt sent with {len(data)} characters")
        return data
        
    def get_check_interval(self) -> float:
        """Get check interval for the run loop"""
        return 0.1  # Check every 100ms
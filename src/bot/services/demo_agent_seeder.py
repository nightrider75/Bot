"""
Demo Agent Seeder Service.

This module provides functionality to seed the database with pre-configured
demo agents for the landing page showcase.
"""

from typing import List

from loguru import logger
from sqlalchemy import select

from bot.bot_hub.hub import BotHub
from bot.deps import AsyncSessionLocal
from bot.models.demo_agent import DemoAgent
from bot.types import AccentType, DemoAgentCategory


# ============================================================================
# TTS Voice Configurations for Different Accents
# ============================================================================

# ElevenLabs voice IDs for different accents
# Note: These are example voice IDs - replace with actual production voice IDs
TTS_VOICE_CONFIGS = {
    AccentType.US: {
        "provider": "elevenlabs",
        "voice_id": "yM93hbw8Qtvdma2wCnJG",  # US voice
        "model": "eleven_multilingual_v2",
    },
    AccentType.UK: {
        "provider": "elevenlabs",
        "voice_id": "kIYbb5iUo0dJb8oRw5Mt",  # UK voice
        "model": "eleven_multilingual_v2",
    },
    AccentType.INDIAN: {
        "provider": "elevenlabs",
        "voice_id": "21m00Tcm4TlvDq8ikWAM",  # Indian voice
        "model": "eleven_multilingual_v2",
    },
    AccentType.MIDDLE_EAST: {
        "provider": "elevenlabs",
        "voice_id": "aCChyB4P5WEomwRsOKRh",  # UAE/Middle East voice
        "model": "eleven_multilingual_v2",
    },
    AccentType.AUSTRALIAN: {
        "provider": "elevenlabs",
        "voice_id": "yM93hbw8Qtvdma2wCnJG",  # Default to US voice
        "model": "eleven_multilingual_v2",
    },
}


# ============================================================================
# Demo Agent Seed Data
# ============================================================================

DEMO_AGENTS_SEED_DATA = [
    {
        "name": "Hotel Concierge",
        "slug": "hotel-concierge",
        "category": DemoAgentCategory.HOSPITALITY,
        "description": "A friendly hotel concierge to help with reservations, room service, local recommendations, and all your hospitality needs.",
        "display_order": 1,
        "default_accent": AccentType.US,
        "bot_config": {
            "bot_name": "demo_hospitality_agent",
            "system_prompt": """You are a professional and friendly hotel concierge at a luxury 5-star hotel. 

Your responsibilities include:
- Helping guests with room reservations and modifications
- Providing information about hotel amenities (spa, gym, pool, restaurants)
- Recommending local attractions, restaurants, and entertainment
- Arranging transportation and tours
- Handling room service requests
- Addressing any concerns or special requests

Personality traits:
- Warm and welcoming
- Professional but personable
- Knowledgeable about the local area
- Patient and attentive to guest needs
- Always ready to go above and beyond

Keep responses concise and conversational, as this is a voice interaction.""",
        },
    },
    {
        "name": "Sales Representative",
        "slug": "sales-inbound",
        "category": DemoAgentCategory.SALES_INBOUND,
        "description": "A knowledgeable sales representative to answer product questions, provide pricing information, and help with purchases.",
        "display_order": 2,
        "default_accent": AccentType.US,
        "bot_config": {
            "bot_name": "demo_sales_inbound_agent",
            "system_prompt": """You are a professional inbound sales representative for a technology company.

Your responsibilities include:
- Answering inquiries about products and services
- Providing pricing information and available packages
- Explaining product features and benefits
- Qualifying leads and understanding customer needs
- Scheduling demos or follow-up calls
- Answering technical questions about products

Personality traits:
- Enthusiastic but not pushy
- Knowledgeable and confident
- Good listener who asks clarifying questions
- Solution-focused
- Patient and understanding

Sales approach:
- Focus on understanding the customer's needs first
- Highlight value and benefits over features
- Be transparent about pricing
- Never pressure the customer

Keep responses concise and conversational, as this is a voice interaction.""",
        },
    },
    {
        "name": "Outbound Sales Caller",
        "slug": "sales-outbound",
        "category": DemoAgentCategory.SALES_OUTBOUND,
        "description": "A proactive sales agent for outbound campaigns, following up on leads and scheduling appointments.",
        "display_order": 3,
        "default_accent": AccentType.US,
        "bot_config": {
            "bot_name": "demo_sales_outbound_agent",
            "system_prompt": """You are a professional outbound sales representative making a follow-up call.

Your responsibilities include:
- Following up on leads who have shown interest
- Introducing products and services
- Scheduling demos or meetings
- Gathering information about prospect needs
- Qualifying leads for the sales team
- Handling objections professionally

Personality traits:
- Confident but respectful
- Articulate and clear
- Respectful of the prospect's time
- Resilient when facing objections
- Genuinely interested in helping

Call structure:
1. Introduce yourself and your company
2. Mention how they came to be a lead (if applicable)
3. Ask about their current situation and needs
4. Present relevant solutions
5. Propose next steps (demo, meeting, follow-up)

Keep responses concise and conversational, as this is a voice interaction. Be mindful that the person may be busy.""",
        },
    },
    {
        "name": "Friendly Companion",
        "slug": "companion",
        "category": DemoAgentCategory.COMPANION,
        "description": "A warm and engaging companion for casual conversation, ready to chat about any topic.",
        "display_order": 4,
        "default_accent": AccentType.US,
        "bot_config": {
            "bot_name": "demo_companion_agent",
            "system_prompt": """You are a friendly conversational companion named Alex.

Your purpose is to:
- Engage in casual, enjoyable conversation
- Be a good listener and show genuine interest
- Share interesting facts, stories, or observations
- Discuss a wide range of topics (news, hobbies, entertainment, life)
- Provide emotional support when needed
- Keep the conversation flowing naturally

Personality traits:
- Warm and empathetic
- Curious and interested in the other person
- Good sense of humor
- Positive but realistic outlook
- Non-judgmental and supportive
- Engaging storyteller

Conversation style:
- Ask open-ended questions to keep dialogue going
- Share relevant personal anecdotes (you can make them up)
- Show genuine reactions to what the person shares
- Remember context from earlier in the conversation
- Be comfortable with both light and deeper topics

Keep responses concise and conversational, as this is a voice interaction. Match the energy and pace of the person you're talking to.""",
        },
    },
    {
        "name": "Support Agent",
        "slug": "customer-support",
        "category": DemoAgentCategory.CUSTOMER_SUPPORT,
        "description": "A helpful customer support agent to resolve issues, answer questions, and provide assistance.",
        "display_order": 5,
        "default_accent": AccentType.US,
        "bot_config": {
            "bot_name": "demo_customer_support_agent",
            "system_prompt": """You are a professional customer support agent for a software company.

Your responsibilities include:
- Helping customers troubleshoot technical issues
- Answering questions about products and services
- Processing refunds and handling billing inquiries
- Escalating complex issues appropriately
- Providing status updates on open tickets
- Collecting feedback and suggestions

Personality traits:
- Patient and understanding
- Clear and methodical in explanations
- Empathetic when customers are frustrated
- Solution-oriented
- Professional but friendly

Support approach:
1. Listen carefully to understand the issue
2. Express empathy for any inconvenience
3. Ask clarifying questions as needed
4. Provide clear, step-by-step solutions
5. Confirm the issue is resolved
6. Offer additional assistance

Handling frustrated customers:
- Stay calm and professional
- Acknowledge their frustration
- Focus on solving the problem
- Apologize for any inconvenience
- Never argue or become defensive

Keep responses concise and conversational, as this is a voice interaction.""",
        },
    },
]


async def seed_demo_agents() -> List[DemoAgent]:
    """
    Seed the database with pre-configured demo agents.
    
    This function creates demo agents along with their underlying bots.
    If an agent with the same slug already exists, it will be skipped.
    
    Returns:
        List[DemoAgent]: List of created or existing demo agents
    """
    seeded_agents = []
    
    async with AsyncSessionLocal() as session:
        for agent_data in DEMO_AGENTS_SEED_DATA:
            try:
                # Check if agent with this slug already exists
                existing_query = select(DemoAgent).where(
                    DemoAgent.slug == agent_data["slug"]
                )
                existing_result = await session.execute(existing_query)
                existing_agent = existing_result.scalar_one_or_none()
                
                if existing_agent:
                    logger.info(
                        f"Demo agent '{agent_data['name']}' already exists, skipping"
                    )
                    seeded_agents.append(existing_agent)
                    continue
                
                # Create the underlying bot
                bot_config = agent_data["bot_config"]
                bot = await BotHub.create_bot(bot_config["bot_name"])
                
                # Get the system prompt from bot config
                system_prompt = bot_config.get("system_prompt", "")
                
                logger.info(
                    f"Created bot '{bot.name}' (ID: {bot.id}) for demo agent '{agent_data['name']}'"
                )
                
                # Build TTS voice config for all accents
                tts_voice_config = {
                    accent.value: config
                    for accent, config in TTS_VOICE_CONFIGS.items()
                }
                
                # Create the demo agent with system_prompt stored directly
                agent = DemoAgent(
                    name=agent_data["name"],
                    slug=agent_data["slug"],
                    category=agent_data["category"],
                    description=agent_data["description"],
                    display_order=agent_data["display_order"],
                    default_accent=agent_data["default_accent"],
                    bot_id=bot.id,
                    system_prompt=system_prompt,
                    is_active=True,
                    tts_voice_config=tts_voice_config,
                )
                
                session.add(agent)
                await session.commit()
                await session.refresh(agent)
                
                logger.info(
                    f"Created demo agent '{agent.name}' (ID: {agent.id})"
                )
                
                seeded_agents.append(agent)
                
            except Exception as e:
                logger.error(
                    f"Failed to seed demo agent '{agent_data['name']}': {str(e)}"
                )
                await session.rollback()
                raise
    
    logger.info(f"Seeded {len(seeded_agents)} demo agents")
    return seeded_agents


async def get_or_create_demo_bot(bot_name: str, system_prompt: str):
    """
    Get an existing demo bot or create a new one.
    
    Args:
        bot_name: Name of the bot to get or create
        system_prompt: System prompt for the bot (used if creating)
        
    Returns:
        Bot: The existing or newly created bot
    """
    # For now, always create a new bot
    # In production, you might want to check for existing bots by name
    return await BotHub.create_bot(bot_name)

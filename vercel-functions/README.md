## Structure of this repo

email-ai-agent/
├── api/
│   ├── email-processor.py      # Main email processing function
│   ├── config-manager.py       # Configuration management API
│   └── health-check.py         # System health endpoint
├── config/
│   ├── email_providers.py      # IMAP settings for providers
│   └── constants.py            # Application constants
├── utils/
│   ├── database.py             # Supabase database utilities
│   ├── email_utils.py          # Email processing utilities
│   ├── ai_utils.py             # AI integration utilities
│   └── telegram_utils.py       # Telegram integration
├── vercel.json                 # Vercel configuration
├── requirements.txt            # Python dependencies
├── .env.local                  # Environment variables
└── README.md                   # Documentation
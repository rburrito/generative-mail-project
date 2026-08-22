SEED_EMAILS = [
    # Thread 1: Phoenix launch timeline (3 emails) - started Dec 28
    {
        "thread_id": "phoenix-timeline-001",
        "sender": "david.park@acme.com",
        "recipient": "pm@acme.com",
        "subject": "Phoenix launch timeline",
        "body": "Alex, wanted to check in on Phoenix. Board is asking about the Q2 launch date. Are we still on track? Any blockers I should know about?",
        "created_at": "2025-12-28T09:15:00",
        "is_read": True
    },
    {
        "thread_id": "phoenix-timeline-001",
        "sender": "pm@acme.com",
        "recipient": "david.park@acme.com",
        "subject": "Re: Phoenix launch timeline",
        "body": "Hi David, we're on track for April 15th. Main risk is the new auth system integration - Sarah's team is working through some edge cases. I'll have a full status report for you by Friday.",
        "created_at": "2025-12-28T10:42:00",
        "is_read": True
    },
    {
        "thread_id": "phoenix-timeline-001",
        "sender": "david.park@acme.com",
        "recipient": "pm@acme.com",
        "subject": "Re: Phoenix launch timeline",
        "body": "Good to hear. Let's plan a quick sync Thursday afternoon if you're free. I want to be prepared for the board call Friday morning.",
        "created_at": "2025-12-28T11:03:00",
        "is_read": True
    },

    # Thread 2: Mobile app offline feature (4 emails) - started Jan 2
    {
        "thread_id": "mobile-offline-002",
        "sender": "sarah.chen@acme.com",
        "recipient": "pm@acme.com",
        "subject": "Mobile v2.0 offline sync - need decision",
        "body": "Hey Alex, we have two options for the offline sync architecture. Option A is simpler but limits us to 50MB local storage. Option B is more complex but gives us 500MB. Which customer segments are we prioritizing here?",
        "created_at": "2026-01-02T14:20:00",
        "is_read": True
    },
    {
        "thread_id": "mobile-offline-002",
        "sender": "pm@acme.com",
        "recipient": "sarah.chen@acme.com",
        "subject": "Re: Mobile v2.0 offline sync - need decision",
        "body": "Good question. Let me check with Jennifer on which segments are pushing hardest for offline. My gut says field sales teams who need the larger storage, but I want to validate. Can you give me until tomorrow EOD?",
        "created_at": "2026-01-02T15:05:00",
        "is_read": True
    },
    {
        "thread_id": "mobile-offline-002",
        "sender": "sarah.chen@acme.com",
        "recipient": "pm@acme.com",
        "subject": "Re: Mobile v2.0 offline sync - need decision",
        "body": "That works. Just FYI, Option B adds about 2 weeks to the timeline. Wanted to make sure that's factored into your decision.",
        "created_at": "2026-01-02T15:18:00",
        "is_read": True
    },
    {
        "thread_id": "mobile-offline-002",
        "sender": "pm@acme.com",
        "recipient": "sarah.chen@acme.com",
        "subject": "Re: Mobile v2.0 offline sync - need decision",
        "body": "Talked to Jennifer. Field sales is our biggest expansion opportunity this quarter. Let's go with Option B. I'll adjust the roadmap and let stakeholders know about the timeline shift.",
        "created_at": "2026-01-03T09:30:00",
        "is_read": True
    },

    # Single email: Team recognition - Jan 6
    {
        "thread_id": "recognition-012",
        "sender": "pm@acme.com",
        "recipient": "sarah.chen@acme.com",
        "subject": "Great work on the API refactor",
        "body": "Sarah, just wanted to say the API refactor your team shipped last week is already paying off. Integration time for new partners dropped from 2 weeks to 3 days. Please pass along my thanks to the team.",
        "created_at": "2026-01-06T16:45:00",
        "is_read": True
    },

    # Thread 3: Design review (2 emails) - Jan 8
    {
        "thread_id": "design-review-003",
        "sender": "marcus.rivera@acme.com",
        "recipient": "pm@acme.com",
        "subject": "Phoenix designs ready for review",
        "body": "Alex, the updated Phoenix mockups are ready. I've addressed the feedback from last week - simplified the onboarding flow and updated the color palette per brand guidelines. Link to Figma: [redacted]. Let me know when you have 30 min to walk through.",
        "created_at": "2026-01-08T11:00:00",
        "is_read": False
    },
    {
        "thread_id": "design-review-003",
        "sender": "pm@acme.com",
        "recipient": "marcus.rivera@acme.com",
        "subject": "Re: Phoenix designs ready for review",
        "body": "These look great, Marcus. Love the simplified onboarding. One thought - can we add a skip option on step 3? Power users have been asking for faster setup. Otherwise good to hand off to eng.",
        "created_at": "2026-01-08T14:22:00",
        "is_read": True
    },

    # Single email: Vendor follow-up - Jan 10
    {
        "thread_id": "vendor-013",
        "sender": "pm@acme.com",
        "recipient": "sales@datavendor.io",
        "subject": "Following up on analytics partnership",
        "body": "Hi, following up on our conversation from last week about integrating your analytics SDK. We'd like to move forward with a pilot. Can you send over the partnership agreement and technical documentation? Thanks, Alex",
        "created_at": "2026-01-10T10:15:00",
        "is_read": True
    },

    # Thread 4: Enterprise dashboard requirements (3 emails) - Jan 13-14
    {
        "thread_id": "enterprise-dash-004",
        "sender": "jennifer.walsh@acme.com",
        "recipient": "pm@acme.com",
        "subject": "Enterprise dashboard - Globex requirements",
        "body": "Alex, just got off a call with Globex. They're very interested in the enterprise dashboard but need SSO integration and custom report exports. They're a $400k/year opportunity. Can we prioritize these features?",
        "created_at": "2026-01-13T16:30:00",
        "is_read": True
    },
    {
        "thread_id": "enterprise-dash-004",
        "sender": "pm@acme.com",
        "recipient": "jennifer.walsh@acme.com",
        "subject": "Re: Enterprise dashboard - Globex requirements",
        "body": "SSO is already on the roadmap for the enterprise tier. Custom exports would be new scope. Can you get more specifics on what formats they need? PDF, CSV, something else? That'll help me size it.",
        "created_at": "2026-01-13T17:05:00",
        "is_read": True
    },
    {
        "thread_id": "enterprise-dash-004",
        "sender": "jennifer.walsh@acme.com",
        "recipient": "pm@acme.com",
        "subject": "Re: Enterprise dashboard - Globex requirements",
        "body": "They need CSV and PDF. Also want to schedule the exports to run weekly. I'll send over their full requirements doc tomorrow.",
        "created_at": "2026-01-14T09:12:00",
        "is_read": False
    },

    # Single email: Data insights - Jan 17
    {
        "thread_id": "data-insights-006",
        "sender": "rachel.kim@acme.com",
        "recipient": "pm@acme.com",
        "subject": "Activation funnel analysis",
        "body": "Alex, finished the activation analysis you requested. Key finding: users who complete the tutorial within 24 hours have 3x higher retention at day 30. Currently only 23% complete it that quickly. Recommend we look at shortening the tutorial or adding incentives. Full report attached.",
        "created_at": "2026-01-17T13:40:00",
        "is_read": True
    },

    # Single email: Competitive intel - Jan 20
    {
        "thread_id": "competitive-011",
        "sender": "jennifer.walsh@acme.com",
        "recipient": "pm@acme.com",
        "subject": "Competitor launched new feature",
        "body": "FYI - Hooli just announced AI-powered analytics in their product. Two prospects mentioned it on calls today. Might be worth discussing at the next product strategy meeting.",
        "created_at": "2026-01-20T11:25:00"
    },

    # Thread 5: Marketing launch prep (2 emails) - Jan 22
    {
        "thread_id": "marketing-launch-007",
        "sender": "lisa.thompson@acme.com",
        "recipient": "pm@acme.com",
        "subject": "Phoenix launch marketing plan",
        "body": "Hey Alex, starting to build out the launch plan for Phoenix. Can you send me the key features we want to highlight? Also need to know if there are any beta customers willing to do testimonials.",
        "created_at": "2026-01-22T10:00:00"
    },
    {
        "thread_id": "marketing-launch-007",
        "sender": "pm@acme.com",
        "recipient": "lisa.thompson@acme.com",
        "subject": "Re: Phoenix launch marketing plan",
        "body": "Top 3 features: 1) Redesigned dashboard with customizable widgets, 2) Real-time collaboration, 3) New API for integrations. For testimonials, check with Jennifer - I think Initech and Umbrella Corp have been happy beta users.",
        "created_at": "2026-01-22T10:45:00",
        "is_read": True
    },

    # Single email: Customer feedback - Jan 24
    {
        "thread_id": "support-feedback-005",
        "sender": "mike.johnson@acme.com",
        "recipient": "pm@acme.com",
        "subject": "Weekly support trends",
        "body": "Hi Alex, here's this week's support summary. Top issues: 1) Users confused by new navigation (32 tickets), 2) Mobile app crashes on Android 12 (18 tickets), 3) Password reset emails delayed (12 tickets). The navigation complaints started after Tuesday's release. Might want to look into that.",
        "created_at": "2026-01-24T09:00:00"
    },

    # Single email: Meeting request - Jan 25
    {
        "thread_id": "meeting-008",
        "sender": "sarah.chen@acme.com",
        "recipient": "pm@acme.com",
        "subject": "Sprint planning Thursday",
        "body": "Alex, can you join sprint planning this Thursday at 10am? We need to finalize the Phoenix punch list and prioritize the remaining bugs. Should take about an hour.",
        "created_at": "2026-01-25T14:30:00"
    },

    # Thread 6: Bug escalation (2 emails) - Jan 26
    {
        "thread_id": "bug-escalation-010",
        "sender": "mike.johnson@acme.com",
        "recipient": "pm@acme.com",
        "subject": "URGENT: Data sync issue affecting Initech",
        "body": "Alex, Initech is reporting that their data hasn't synced in 3 hours. They're a key beta customer for Phoenix. I've escalated to Sarah's team but wanted you in the loop. This could affect the testimonial ask.",
        "created_at": "2026-01-26T15:45:00"
    },
    {
        "thread_id": "bug-escalation-010",
        "sender": "pm@acme.com",
        "recipient": "mike.johnson@acme.com",
        "subject": "Re: URGENT: Data sync issue affecting Initech",
        "body": "Thanks for flagging, Mike. I'll reach out to their account manager directly. Keep me posted on the fix ETA.",
        "created_at": "2026-01-26T16:02:00",
        "is_read": True
    },

    # Single email: PM sending status update - Jan 26
    {
        "thread_id": "status-009",
        "sender": "pm@acme.com",
        "recipient": "david.park@acme.com",
        "subject": "Weekly product update - Jan 26",
        "body": "David, here's this week's update:\n\nPhoenix: On track for April 15. Design approved, eng at 75% complete.\n\nMobile v2.0: Decided on expanded offline storage. Adds 2 weeks but unlocks field sales segment.\n\nEnterprise Dashboard: Scoping custom exports for Globex ($400k opportunity).\n\nBlockers: None currently.\n\nLet me know if you have questions.",
        "created_at": "2026-01-26T16:15:00",
        "is_read": True
    },
]

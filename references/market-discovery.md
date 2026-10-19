# Market Discovery Skill (v1.0)

## Overview
**Purpose**: When users express a new product idea, this skill performs comprehensive market research across App Store, GitHub, Google Web, and Xiaohongshu, then generates a detailed feasibility report with screenshots, links, ratings, and competitor analysis.

**Trigger Logic**: 
- Detects product ideas from user input
- **Asks for confirmation before executing** (两步走流程)
- Only runs after user explicitly confirms

---

## Trigger Detection

### Keywords that trigger confirmation prompt:
- "我想做一个..." / "I want to make..."
- "有个 idea..." / "Got an idea..."
- "要不要做..." / "Should we build..."
- "[产品名] feasibility" / "[product] viability"
- "XXX 产品如何..." / "How about XXX product..."

### Response Pattern:
```
📊 检测到新产品想法：[提取关键词]

是否需要启动 Market Discovery 调研？

【确认调研】→ Enter Phase 2
【稍后再说】→ Record only, no execution
【不需要】→ End conversation
```

---

## Execution Protocol (After Confirmation)

### Data Source Priority

1. **App Store / Google Play** - Commercial products
   - Extract: Name, Link, Screenshot (≥3 key screens), Rating, Download count, Pricing model
   
2. **GitHub** - Open-source projects (even if not published)
   - Extract: Repository link, Star count, Last update date, Issue response speed, Code quality indicators
   
3. **Google Web** - Websites, reviews, articles
   - Extract: Official site, Tech review blogs, Comparison articles, Video demos
   
4. **小红书** - Domestic alternatives in China
   - Extract: User posts, Reviews, Alternative solutions mentioned

### Data Collection Fields (Per Competitor)

For each identified competitor/product:

| Field | Format | Notes |
|-------|--------|-------|
| 📱 Product name + Link | Text + URL | Direct link to store repo or official page |
| 🖼️ Key screen screenshots | ≥3 images | Homepage, Core feature, Settings/Detail |
| ⭐ Rating + Usage metrics | Score + Count | 4.5★ (1.2k reviews) / 15k Stars |
| 💬 Top 5 reviews summary | Positive/Negative | Extract common praise/complaints |
| 💰 Pricing model | Free / Freemium / $X/month | Include IAP details if any |
| 🔍 Last updated | Date format | "2026-09-15" or "Updated weekly" |
| ⚠️ GitHub health issues | Text | Open bugs, slow issue response, etc. |

---

## Report Output Structure

### Format: Markdown (with embedded image references)

```markdown
# [Product Name] Market Research Report
Generated: YYYY-MM-DD HH:MM

## A. Market Overview
- **Total similar products**: X commercial + Y open-source
- **Market concentration**: Top 3 competitors control ~Z% share
- **Differentiation opportunities**:
  1. [Opportunity 1 - e.g., "Better onboarding flow"]
  2. [Opportunity 2 - e.g., "More transparent pricing"]
  3. [Opportunity 3 - e.g., "Local language support gap"]

## B. Competitor Comparison Table
| Dimension | Competitor A | Competitor B | Competitor C | Our Recommendation |
|-----------|--------------|--------------|--------------|---------------------|
| Price     | $9.99/month | Free         | Freemium     | $7.99/month (entry tier) |
| Core Features | Limited      | Missing X    | Too complex  | Focus on X+Y middle ground |
| User Pain Points | Old UI       | Expensive    | Steep learning curve | Emphasize simplicity |
| Update Frequency | Monthly     | Quarterly    | Weekly       | Set monthly cadence |

## C. Prototype Reference Library
✅ **Patterns to借鉴** (with screenshots):
- [Pattern 1]: [Description] → [Screenshot link]
- [Pattern 2]: [Description] → [Screenshot link]

⚠️ **Pitfalls to avoid** (from negative reviews):
- [Pitfall 1]: [What users hate] - Source: App Store review #123
- [Pitfall 2]: [Technical limitation] - Source: GitHub issue #456

## D. Feasibility Conclusion
**Verdict**: ⭐ Recommendable / ⚠️ Caution / ❌ Not recommended

### Rationale:
- **Strengths**: [Why it's viable]
- **Risks**: [Known barriers/challenges]
- **Next steps**: [Design brief → Flow design → QA]

---
**Sources**: All data points have source links/screenshots attached.
**Confidence Level**: High/Medium/Low (based on data completeness)
```

---

## Special Rules & Constraints

### 1. Cost Transparency
- Before running API-heavy searches, inform user of estimated API calls/costs
- Example: "This will use 3 web search queries + 1 App Store lookup (~$0.X)"

### 2. Evidence Chain Requirement
- Every data point must cite a source link or screenshot
- Never say "there are many competitors" without specific examples
- Empty results = explicit statement like "No similar products found on GitHub"

### 3. No Result Handling
- If App Store returns zero matches: "该品类暂无商业化产品，可能是蓝海机会或需求不存在"
- If GitHub has no opensource: "开源生态暂无同类项目，可考虑 fork  closest match"
- If Xiaohongshu empty: "国内讨论较少，建议聚焦海外市场"

### 4. Privacy Boundary
- Do NOT query paid APIs requiring user authentication
- Do NOT access private repositories without explicit permission
- Stick to publicly accessible information only

### 5. Freshness Validation
- All screenshots must be fresh (captured during this session)
- For dynamic data (e.g., download counts), note the timestamp
- Cross-check dates: if last update > 6 months ago, mark as "potentially abandoned"

---

## Integration with Product-Design Suite

```
Workflow Chain:

[User Idea]
    ↓
[Market Discovery] ← This skill (feasibility validation)
    ↓ (if feasible)
[Design Brief] /brief (direction alignment)
    ↓
[Sitemap] /sitemap (IA structure)
    ↓
[Stories] /stories (user story breakdown)
    ↓
[Flow Design] /flow-web or /flow-mobile (multi-screen specs)
    ↓
[Design QA] /check (pre-launch validation)
```

### Handoff Points:
- **To Design Brief**: Pass differentiation opportunities + target user profile
- **To Flow Design**: Pass prototype patterns that worked well for competitors
- **To Design QA**: Pass known pitfalls to explicitly validate against

---

## Example Interaction

### Scenario: User wants to build AI writing assistant

```
User: "我想做一个 macOS 上的 AI 写作助手，能自动整理笔记生成文章"

AI: 📊 检测到新产品想法：macOS AI 写作助手自动生成文章

是否需要启动 Market Discovery 调研？

【确认调研】【稍后再说】【不需要】

[User clicks 确认调研]

→ Executes: App Store search → GitHub repos → Google reviews → Xiaohongshu
→ Generates: Full report with 5 competitors, 15 screenshots, comparison table
→ Outputs: Feasibility verdict + next step recommendation
```

---

## Version History

- v1.0 (2026-09-21): Initial release with 4-channel coverage + confirmation workflow

---

## File Location
Path: `/Users/hangzhou/Desktop/_工具脚本/skills/market-discovery.md`

## Maintenance Owner
[Your team/project name here]

## Related Skills
- `/brief` - Design brief generation
- `/probe` - User research interviews  
- `/bench` - Competitor UX deep-dive
- `/prd` - Engineering handoff documentation

# Agentic AI Reading Canon

A practical reading curriculum for applied LLM and agent engineering. It
combines foundational papers with high-value engineering guidance from
Anthropic, OpenAI, and influential researchers.

> **How to use this list:** Read Tier 1 carefully, understand the main
> ideas in Tier 2, and use Tier 3 as a reference when a project requires
> it. The goal is not academic completeness; it is to understand the
> ideas that shape modern agent systems.

## 1. LLM Foundations

1.  **[Attention Is All You Need](https://arxiv.org/pdf/1706.03762)** --- Vaswani et al. (2017)\
    Transformer architecture. Understand self-attention, positional
    information, and why the architecture displaced recurrent models.

2.  **[Language Models are Few-Shot Learners (GPT-3)](https://arxiv.org/pdf/2005.14165)** --- Brown et
    al. (2020)\
    Scaling and in-context learning.

3.  **[Scaling Laws for Neural Language Models](https://arxiv.org/pdf/2001.08361)** --- Kaplan et
    al. (2020)\
    Empirical relationships between model size, data, compute, and loss.

4.  **[Training Compute-Optimal Large Language Models (Chinchilla)](https://arxiv.org/pdf/2203.15556)** ---
    Hoffmann et al. (2022)\
    Why scaling model parameters without sufficient training data is
    inefficient.

5.  **[Training Language Models to Follow Instructions with Human
    Feedback (InstructGPT)](https://arxiv.org/pdf/2203.02155)** --- Ouyang et al. (2022)\
    SFT, preference data, reward modeling, and RLHF.

6.  **[Constitutional AI: Harmlessness from AI Feedback](https://arxiv.org/pdf/2212.08073)** --- Bai et al.,
    Anthropic (2022)\
    AI feedback and constitutional principles as an
    alternative/complement to human preference supervision.

## 2. Reasoning and Prompting

7.  **[Chain-of-Thought Prompting Elicits Reasoning in Large Language
    Models](https://arxiv.org/pdf/2201.11903)** --- Wei et al. (2022)\
    The foundational chain-of-thought result.

8.  **[Large Language Models are Zero-Shot Reasoners](https://arxiv.org/pdf/2205.11916)** --- Kojima et
    al. (2022)\
    Shows that reasoning behavior can be elicited without worked
    examples.

9.  **[Self-Consistency Improves Chain of Thought Reasoning in Language
    Models](https://arxiv.org/pdf/2203.11171)** --- Wang et al. (2022/23)\
    Sample multiple reasoning paths and aggregate answers.

10. **[Least-to-Most Prompting Enables Complex Reasoning in Large
    Language Models](https://arxiv.org/pdf/2205.10625)** --- Zhou et al. (2022)\
    Decompose difficult problems into simpler subproblems.

11. **[STaR: Self-Taught Reasoner](https://arxiv.org/pdf/2203.14465)** --- Zelikman et al. (2022)\
    Bootstrapping reasoning from model-generated rationales.

12. **[Tree of Thoughts: Deliberate Problem Solving with Large Language
    Models](https://arxiv.org/pdf/2305.10601)** --- Yao et al. (2023)\
    Search over multiple intermediate reasoning states.

13. **[Self-Refine: Iterative Refinement with Self-Feedback](https://arxiv.org/pdf/2303.17651)** --- Madaan
    et al. (2023)\
    Generate, critique, and iteratively improve.

14. **[Reflexion: Language Agents with Verbal Reinforcement Learning](https://arxiv.org/pdf/2303.11366)**
    --- Shinn et al. (2023)\
    Agents use textual feedback from previous attempts to improve
    subsequent attempts.

**Conceptual progression:** chain of thought → sampling/verification →
decomposition → search → reflection → loops.

## 3. Foundational Tool and Agent Papers

15. **[ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/pdf/2210.03629)** ---
    Yao et al. (2022/23)\
    Essential. Interleaves reasoning, actions, and observations. One of
    the clearest ancestors of the modern agent loop.

16. **[Toolformer: Language Models Can Teach Themselves to Use Tools](https://arxiv.org/pdf/2302.04761)**
    --- Schick et al. (2023)\
    Models learn when and how external tools are useful.

17. **[MRKL Systems: A Modular, Neuro-Symbolic Architecture That Combines
    Large Language Models, External Knowledge Sources and Discrete
    Reasoning](https://arxiv.org/pdf/2205.00445)** --- Karpas et al. (2022)\
    Early modular architecture for routing work from an LLM to
    specialized systems.

18. **[PAL: Program-Aided Language Models](https://arxiv.org/pdf/2211.10435)** --- Gao et al. (2022/23)\
    Let the model construct programs and delegate deterministic
    computation to an interpreter.

19. **[ART: Automatic Multi-step Reasoning and Tool-use for Large
    Language Models](https://arxiv.org/pdf/2303.09014)** --- Paranjape et al. (2023)\
    Combines decomposition, reasoning, and tools.

20. **[Gorilla: Large Language Model Connected with Massive APIs](https://arxiv.org/pdf/2305.15334)** ---
    Patil et al. (2023)\
    API selection and invocation at large scale.

## 4. Modern Agent Engineering --- Anthropic

21. **[Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)** --- Anthropic\
    **Must read.** Distinguishes workflows from agents and explains
    prompt chaining, routing, parallelization, orchestrator-worker, and
    evaluator-optimizer patterns.

22. **[The "Think" Tool: Enabling Claude to Stop and Think in Complex
    Tool Use Situations](https://www.anthropic.com/engineering/claude-think-tool)** --- Anthropic\
    Shows how a small harness/tool change can materially affect agent
    performance.

23. **[Claude Code: Best Practices for Agentic Coding](https://www.anthropic.com/engineering/claude-code-best-practices)** --- Anthropic\
    Practical lessons for coding-agent workflows.

24. **[How We Built Our Multi-Agent Research System](https://www.anthropic.com/engineering/multi-agent-research-system)** --- Anthropic\
    One of the best production descriptions of orchestrator/subagent
    architecture.

25. **[Writing Effective Tools for Agents --- With Agents](https://www.anthropic.com/engineering/writing-tools-for-agents)** ---
    Anthropic\
    **Must read.** Tool interfaces, schemas, descriptions, and responses
    are part of agent engineering.

26. **[Effective Context Engineering for AI Agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)** --- Anthropic\
    **Must read.** Context is scarce; provide the smallest high-signal
    context necessary and retrieve information just in time.

27. **[Equipping Agents for the Real World with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)** ---
    Anthropic\
    Skills as progressively discoverable procedural/domain knowledge
    rather than permanent prompt content.

28. **[Code Execution with MCP: Building More Efficient Agents](https://www.anthropic.com/engineering/code-execution-with-mcp)** ---
    Anthropic\
    Explores programmable interfaces as an alternative to exposing very
    large numbers of individual tool calls.

29. **[Advanced Tool Use / Tool Search](https://www.anthropic.com/engineering/advanced-tool-use)** --- Anthropic\
    Capability discovery and scaling large tool catalogs.

30. **[Effective Harnesses for Long-Running Agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)** --- Anthropic\
    State, checkpoints, environment feedback, tests, context management,
    and recovery for work spanning multiple agent iterations.

31. **[Harness Design for Long-Running Application Development](https://www.anthropic.com/engineering)** ---
    Anthropic\
    Further practical guidance on building the environment around
    long-running coding agents.

32. **[Scaling Managed Agents: Decoupling the Brain from the Hands](https://www.anthropic.com/engineering/scaling-managed-agents)** ---
    Anthropic\
    Architectural separation between reasoning/orchestration and
    execution.

33. **[Building a C Compiler with a Team of Parallel Claudes](https://www.anthropic.com/engineering/building-a-c-compiler-with-a-team-of-parallel-claudes)** ---
    Anthropic\
    Concrete case study of parallel agents and decomposition.

Anthropic Engineering index: https://www.anthropic.com/engineering

## 5. OpenAI Agent Engineering

34. **[A Practical Guide to Building AI Agents](https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/)** --- OpenAI\
    **Must read.** Model + tools + instructions, agent loops,
    orchestration, guardrails, and single-agent versus multi-agent
    architecture.

35. **[OpenAI Agents SDK --- Documentation and Design Concepts](https://openai.github.io/openai-agents-python/)**\
    Understand loops, tools, handoffs, tracing, guardrails, and
    practical orchestration.

36. **[Inside OpenAI's In-House Data Agent](https://openai.com/index/inside-our-in-house-data-agent/)** --- OpenAI\
    Production case study involving enterprise data, permissions, tools,
    and workflows.

37. **[ChatGPT Agent: Bridging Research and Action](https://openai.com/index/introducing-chatgpt-agent/)** --- OpenAI\
    Useful view of combining browsing, code execution, tools, and
    interaction into a general agent.

38. **[OpenAI Model Spec](https://model-spec.openai.com/)** --- OpenAI\
    Important for instruction hierarchy, authority, tool behavior, user
    intent, and agent boundaries.

## 6. Context, Retrieval, and Knowledge

39. **[Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks](https://arxiv.org/pdf/2005.11401)**
    --- Lewis et al. (2020)\
    The foundational RAG paper.

40. **[Dense Passage Retrieval for Open-Domain Question Answering (DPR)](https://arxiv.org/pdf/2004.04906)**
    --- Karpukhin et al. (2020)\
    Foundational dense retrieval approach.

41. **[ColBERT: Efficient and Effective Passage Search via Contextualized
    Late Interaction](https://arxiv.org/pdf/2004.12832)** --- Khattab & Zaharia (2020)\
    Late interaction between query and document token representations.

42. **[Precise Zero-Shot Dense Retrieval without Relevance Labels
    (HyDE)](https://arxiv.org/pdf/2212.10496)** --- Gao et al. (2022/23)\
    Generate a hypothetical relevant document and use it to retrieve
    real documents.

43. **[Introducing Contextual Retrieval](https://www.anthropic.com/news/contextual-retrieval)** --- Anthropic\
    Adds document-level context to chunks before embedding/indexing to
    reduce retrieval failures.

44. **[Effective Context Engineering for AI Agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)** --- Anthropic\
    Also belongs here because retrieval is only one mechanism for
    deciding what enters the context window.

**Conceptual progression:** keyword search → dense retrieval → hybrid
retrieval → reranking → contextualized chunks → agentic search →
progressive disclosure.

## 7. Memory and Autonomous Agents

45. **[Generative Agents: Interactive Simulacra of Human Behavior](https://arxiv.org/pdf/2304.03442)** ---
    Park et al. (2023)\
    Memory stream, reflection, retrieval, and planning.

46. **[Voyager: An Open-Ended Embodied Agent with Large Language Models](https://arxiv.org/pdf/2305.16291)**
    --- Wang et al. (2023)\
    Particularly important for its accumulating skill library and
    automatic curriculum.

47. **[MemGPT: Towards LLMs as Operating Systems](https://arxiv.org/pdf/2310.08560)** --- Packer et
    al. (2023)\
    Treats the context window as scarce working memory and external
    storage as managed memory.

These are useful conceptual predecessors of progressive disclosure: the
complete information environment does not need to exist in the active
context.

## 8. Multi-Agent Systems

48. **[AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent
    Conversation](https://arxiv.org/pdf/2308.08155)** --- Microsoft Research (2023)\
    Framework and architecture for conversational multi-agent
    applications.

49. **[CAMEL: Communicative Agents for Mind Exploration of Large Scale
    Language Model Society](https://arxiv.org/pdf/2303.17760)** --- Li et al. (2023)\
    Role-playing and communication between agents.

50. **[How We Built Our Multi-Agent Research System](https://www.anthropic.com/engineering/multi-agent-research-system)** --- Anthropic\
    Production evidence for orchestrator-worker systems and parallel
    research.

**Important:** Multiple agents are not inherently better. Require a
concrete benefit such as parallel exploration, context isolation,
specialization, adversarial checking, or independently executable work.

## 9. Evals and Benchmarks

51. **[Demystifying Evals for AI Agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)** --- Anthropic\
    **Must read.** Practical methodology for agent evaluation.

52. **[Designing AI-Resistant Technical Evaluations](https://www.anthropic.com/engineering/designing-ai-resistant-technical-evaluations)** --- Anthropic\
    Designing evaluations that remain meaningful as models become
    increasingly capable.

53. **[Quantifying Infrastructure Noise in Agentic Coding Evals](https://www.anthropic.com/engineering/quantifying-infrastructure-noise-in-agentic-coding-evals)** ---
    Anthropic\
    Shows that the harness/environment can materially affect measured
    benchmark performance.

54. **[Eval Awareness in Claude's BrowseComp Performance](https://www.anthropic.com/engineering/eval-awareness-in-claudes-browsecomp-performance)** --- Anthropic\
    Useful for understanding benchmark awareness and evaluation
    validity.

55. **[SWE-bench: Can Language Models Resolve Real-World GitHub Issues?](https://arxiv.org/pdf/2310.06770)**
    --- Jimenez et al.\
    One of the most important benchmarks for coding agents.

56. **[SWE-bench Verified](https://www.swebench.com/SWE-bench_Verified.html)**\
    Human-validated subset intended to improve benchmark quality.

57. **[GDPval](https://openai.com/index/gdpval/)** --- OpenAI\
    Moves evaluation toward economically meaningful real-world tasks.

58. **[Predicting Model Behavior Before Release by Simulating
    Deployment](https://openai.com/index/predicting-model-behavior-before-release/)** --- OpenAI\
    Agentic trajectories, tool simulation, and evaluation-awareness
    concerns.

59. **[Bloom: Automated Behavioral Evaluations](https://www.anthropic.com/engineering/bloom-automated-behavioral-evaluations)** --- Anthropic\
    Agentic generation of behavioral evaluations.

60. **[A Shared Playbook for Trustworthy Third-Party Evaluations](https://openai.com/index/a-shared-playbook-for-trustworthy-third-party-evaluations/)** ---
    OpenAI\
    Emphasizes reporting model, harness, tools, inference budget,
    retries, costs, elicitation, and validity.

**Engineering rule:** an agent capability without an evaluation harness
is not yet a reliably engineered capability.

## 10. Safety and Trustworthy Agents

61. **[Constitutional AI](https://arxiv.org/pdf/2212.08073)** --- Anthropic\
    Foundational alignment work; also listed above.

62. **[Sleeper Agents: Training Deceptive LLMs that Persist Through
    Safety Training](https://arxiv.org/pdf/2401.05566)** --- Anthropic et al.\
    Important work on persistent deceptive behavior.

63. **[Auditing Language Models for Hidden Objectives](https://www.anthropic.com/research)** --- Anthropic\
    Methods and challenges for detecting hidden objectives.

64. **[Trustworthy Agents in Practice](https://www.anthropic.com/engineering)** --- Anthropic\
    Human control, user expectations, secure interactions, transparency,
    and privacy.

65. **[OpenAI--Anthropic Joint Alignment Evaluation Exercise](https://www.anthropic.com/research)**\
    Cross-lab evaluation of agentic behaviors including deception,
    sandbagging, reward hacking, and tool misuse.

66. **[Chain-of-Thought Monitoring / Controllability Research](https://openai.com/index/chain-of-thought-monitoring/)** ---
    OpenAI\
    Important emerging direction for monitoring reasoning models.

67. **[Beyond Permission Prompts: Making Claude Code More Secure and
    Autonomous](https://www.anthropic.com/engineering/beyond-permission-prompts)** --- Anthropic\
    Security architecture beyond asking the user to approve every
    operation.

68. **[How We Contain Claude Across Products](https://www.anthropic.com/engineering/how-we-contain-claude-across-products)** --- Anthropic\
    Useful framing around capabilities, isolation, containment, and
    blast radius.

**Security principle:** distinguish model behavior from actual system
capability. Enforce critical boundaries outside the model using least
privilege, isolation, deterministic policy, and auditable tools.

## 11. Interpretability

69. **[Toy Models of Superposition](https://arxiv.org/pdf/2209.10652)** --- Anthropic\
    Foundational conceptual work on superposition.

70. **[Towards Monosemanticity](https://transformer-circuits.pub/2023/monosemantic-features/index.html)** --- Anthropic\
    Dictionary learning and interpretable features.

71. **[Scaling Monosemanticity](https://transformer-circuits.pub/2024/scaling-monosemanticity/index.html)** --- Anthropic\
    Applying feature extraction at production-model scale.

72. **[Tracing the Thoughts of a Large Language Model](https://www.anthropic.com/research/tracing-thoughts-language-model)** --- Anthropic\
    Mechanistic investigation of internal computation.

73. **[Circuit Tracing / Open Circuit-Tracing Tools](https://www.anthropic.com/research)** --- Anthropic\
    Practical tools for investigating model mechanisms.

This is important background knowledge, but lower priority for an
applied agent engineer than tools, context, harnesses, evals, and
security.

## 12. High-Value Syntheses by Individual Researchers

74. **[LLM Powered Autonomous Agents](https://lilianweng.github.io/posts/2023-06-23-agent/)** --- Lilian Weng\
    **Must read.** Excellent synthesis of planning, memory, tool use,
    reflection, and agent architectures.

75. **[Prompt Engineering](https://lilianweng.github.io/posts/2023-03-15-prompt-engineering/)** --- Lilian Weng\
    Broad technical overview of prompting approaches.

76. **[Reward Hacking in Reinforcement Learning](https://lilianweng.github.io/posts/2024-11-28-reward-hacking/)** --- Lilian Weng\
    Useful foundation for understanding specification gaming and reward
    hacking.

77. **[Extrinsic Hallucinations in LLMs](https://lilianweng.github.io/posts/2024-09-05-hallucination/)** --- Lilian Weng\
    Useful synthesis of hallucination mechanisms and mitigation
    approaches.

------------------------------------------------------------------------

# Recommended Core Reading List

If time is limited, start with these roughly 20 sources.

1.  **[Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)** --- Anthropic
2.  **[A Practical Guide to Building AI Agents](https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/)** --- OpenAI
3.  **[ReAct](https://arxiv.org/pdf/2210.03629)** --- Yao et al.
4.  **[Toolformer](https://arxiv.org/pdf/2302.04761)** --- Schick et al.
5.  **[Effective Context Engineering for AI Agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)** --- Anthropic
6.  **[Writing Effective Tools for Agents](https://www.anthropic.com/engineering/writing-tools-for-agents)** --- Anthropic
7.  **[Equipping Agents for the Real World with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)** ---
    Anthropic
8.  **[Code Execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp)** --- Anthropic
9.  **[How We Built Our Multi-Agent Research System](https://www.anthropic.com/engineering/multi-agent-research-system)** --- Anthropic
10. **[Effective Harnesses for Long-Running Agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)** --- Anthropic
11. **[OpenAI Model Spec](https://model-spec.openai.com/)**
12. **[Retrieval-Augmented Generation](https://arxiv.org/pdf/2005.11401)** --- Lewis et al.
13. **[Introducing Contextual Retrieval](https://www.anthropic.com/news/contextual-retrieval)** --- Anthropic
14. **[Reflexion](https://arxiv.org/pdf/2303.11366)** --- Shinn et al.
15. **[Generative Agents](https://arxiv.org/pdf/2304.03442)** --- Park et al.
16. **[Voyager](https://arxiv.org/pdf/2305.16291)** --- Wang et al.
17. **[Demystifying Evals for AI Agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)** --- Anthropic
18. **[SWE-bench](https://arxiv.org/pdf/2310.06770) / [SWE-bench Verified](https://www.swebench.com/SWE-bench_Verified.html)**
19. **[Trustworthy Agents in Practice](https://www.anthropic.com/engineering)** --- Anthropic
20. **[LLM Powered Autonomous Agents](https://lilianweng.github.io/posts/2023-06-23-agent/)** --- Lilian Weng

## Suggested Priority

### Tier 1 --- Read carefully

Focus on approximately 20 sources covering:

-   ReAct
-   Toolformer
-   Reflexion
-   Building Effective Agents
-   Practical Guide to Building AI Agents
-   Effective Context Engineering
-   Writing Effective Tools
-   Agent Skills
-   MCP/code execution
-   Multi-Agent Research System
-   Long-running agent harnesses
-   OpenAI Model Spec
-   RAG and modern retrieval
-   Generative Agents
-   Voyager
-   agent eval methodology
-   SWE-bench
-   trustworthy-agent/security engineering
-   Lilian Weng's agent synthesis

### Tier 2 --- Understand

Know the core ideas from:

-   scaling laws and Chinchilla
-   InstructGPT
-   Chain-of-Thought
-   Self-Consistency
-   Tree of Thoughts
-   Self-Refine
-   PAL
-   DPR / ColBERT / HyDE
-   Contextual Retrieval
-   MemGPT
-   AutoGen / CAMEL
-   Claude Code engineering
-   advanced tool use
-   evaluation methodology
-   interpretability

### Tier 3 --- Reference When Needed

Use specialized alignment, interpretability, benchmark, multi-agent, and
architecture papers when a concrete project requires them.

------------------------------------------------------------------------

# The Mental Model to Keep

The papers are easier to understand as an engineering progression:

**LLMs**\
→ reasoning\
→ decomposition\
→ tools\
→ observations and loops\
→ retrieval\
→ context engineering\
→ memory\
→ skills\
→ agents\
→ multi-agent orchestration\
→ harness engineering\
→ evals\
→ observability\
→ security and containment

The modern engineering lesson is that model capability is only one part
of a successful agent system.

A production-quality agent is better thought of as:

**model + instructions + context + tools + environment + state + loop +
policy + observability + evals**

As models improve, engineering effort increasingly shifts from clever
prompting toward the **system surrounding the model**: tool design,
context management, retrieval, state, feedback, tests, permissions,
tracing, recovery, and rigorous evaluation.

------------------------------------------------------------------------

## Key Reference Hubs

-   Anthropic Engineering: https://www.anthropic.com/engineering
-   Anthropic Research: https://www.anthropic.com/research
-   OpenAI Research: https://openai.com/research/
-   OpenAI Model Spec: https://model-spec.openai.com/
-   OpenAI Agents SDK: https://openai.github.io/openai-agents-python/
-   Lilian Weng: https://lilianweng.github.io/
-   SWE-bench: https://www.swebench.com/

------------------------------------------------------------------------

*Last consolidated: August 2026. This is intended as a living reading
list; prioritize enduring concepts over framework-specific APIs.*

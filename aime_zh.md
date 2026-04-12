# Aime：迈向完全自主多智能体框架

**AimeTeam**
Yexuan Shi*, Mingyu Wang, Yunxiang Cao, Hongjie Lai, Junjian Lan, Xin Han, Yu Wang, Jie Geng, Zhenan Li, Zihao Xia, Xiang Chen, Chen Li, Jian Xu, Wenbo Duan, Yuanshuo Zhu
ByteDance

---

## 摘要

由大语言模型（LLM）驱动的多智能体系统（MAS）正在成为解决复杂、多面问题的强大范式。然而，这些系统的潜力往往受到普遍存在的计划-执行框架的限制，该框架存在以下关键缺陷：僵化的计划执行、静态的智能体能力以及低效的通信。这些弱点阻碍了它们在动态环境中的适应性和鲁棒性。本文介绍了 **Aime**，这是一种新颖的多智能体框架，旨在通过动态、响应式的规划和执行来克服这些挑战。Aime用流畅且自适应的架构取代了传统的静态工作流。其核心创新包括：(1) **动态规划器**（Dynamic Planner），它根据实时执行反馈不断改进整体策略；(2) **Actor工厂**（Actor Factory），它实现了动态Actor实例化，按需组装专门的智能体，并配备定制的工具和知识；(3) **集中式进度管理模块**（Progress Management Module），作为统一的真值来源，实现连贯的全系统状态感知。我们在涵盖通用推理（GAIA）、软件工程（SWE-bench Verified）和实时网页导航（WebVoyager）的多样化基准套件上对Aime进行了实证评估。结果表明，Aime在各自领域始终优于高度专业化的现有智能体。其卓越的适应性和任务成功率确立了Aime作为多智能体协作更具弹性和有效性的基础。

---

## 1 引言

大语言模型（LLM）的近期出现是人工智能发展史上的一个重要里程碑（Chang et al., 2024）。LLM在自然语言理解、推理和生成方面展示了深厚的能力，现已成为新型智能系统的基础技术。这一趋势推动了LLM智能体的发展：利用LLM作为其核心认知引擎的自主实体。通过用外部工具（如代码解释器或信息检索系统）增强LLM，这些智能体可以与环境交互，执行复杂的多步骤任务，成为通用且自主的问题解决者（Wang et al., 2024b; Qin et al., 2024; Wang et al., 2024a）。

在单个智能体成功的基础上，该领域越来越多地探索多智能体系统（MAS），其中LLM智能体团队协作解决超出单个智能体能力范围的复杂问题。这种范例因其能够分解大规模问题并以协同方式利用专业化智能体而受到重视（Shen et al., 2023; Hong et al., 2024; Tao et al., 2024）。在各种架构中，**计划-执行框架**已成为主导方法（Huang et al., 2024）。在该结构中，专门的规划智能体将用户请求解构为静态的子任务序列。这些子任务随后被分配给执行智能体团队，每个智能体都具有预定义的角色和工具集。

尽管该范式被广泛采用，但计划-执行模型表现出关键局限性，特别是在动态或不可预测的环境中。规划和执行的严格分离带来了显著的操作摩擦。我们的工作指出了三个限制这些系统有效性的基本挑战：

(1) **僵化的计划执行**。计划生成一次后通常很脆弱。规划器在执行期间保持空闲，使得系统无法根据执行器产生的实时反馈或意外结果进行调整。

(2) **静态智能体能力**。智能体被限制在预定义的角色和工具集中。这种刚性限制了系统处理需要新技能的不可预见任务的能力，从而损害了其可扩展性和鲁棒性。

(3) **低效通信**。智能体之间的任务交接通常会导致上下文丢失。如果没有集中式状态管理系统，智能体在对整体进度不完整的视图下操作，导致冗余工作和协调失败。

为了解决这些限制，本文介绍**Aime**，一个为动态、响应式规划和执行设计的新颖多智能体框架。Aime不采用静态的自上而下工作流，而是基于持续适应的原则运行。它用更流畅的架构取代了固定的规划器-执行器二分法，包含四个核心组件：

- **动态规划器**：根据实时反馈持续改进策略
- **Actor工厂**：按需实例化专门的Actor以满足特定任务需求
- **自主动态Actor**：执行任务
- **集中式进度管理模块**：作为全系统状态感知的统一真值来源

本文的主要贡献如下：

- 我们提出了Aime，一个新颖的多智能体系统框架，它用流畅、自适应的系统取代了僵化的计划-执行范式。Aime支持动态计划调整、按需角色分配和简化的协调，以有效管理复杂、不断演变的任务。

- 我们引入了**动态Actor实例化**，这是一种通过Actor工厂实现的机制。该组件按需组装专门的Actor，为它们配备定制的角色、工具和知识，以解决静态智能体角色的局限。

- 我们设计了集中式进度管理模块，维护统一的任务进度实时视图。该模块通过提供整个系统连贯的状态感知，缓解了信息丢失和协调失败问题。

- 我们在具有挑战性的基准上进行了全面实验，涵盖通用推理、软件工程和网页导航（GAIA、SWE-bench、WebVoyager）。我们的结果表明，它在任务成功率和适应性方面均显著优于专门的现有框架。

本文的其余部分组织如下：第2节提供了LLM智能体和多智能体系统的详细背景。第3节概述了Aime框架。第4节详细介绍了其核心组件的设计。实验设置和结果在第5节中展示。我们在第6节讨论相关工作，最后在第7节总结全文。

---

## 2 背景

本节回顾了大语言模型智能体（LLM智能体）和多智能体系统（MAS）的核心概念。然后讨论当前挑战并阐述我们的研究动机。

**LLM智能体**。大语言模型（LLM）的出现催生了一类新型自主系统——LLM智能体。LLM智能体将LLM不仅用作文本生成器，而且用作推理、规划和决策的核心认知引擎（Yao et al., 2023）。为了超越其静态预训练知识的固有局限，这些智能体被增强了外部工具。这种增强允许它们与环境动态交互，赋予它们执行代码、检索实时网络信息和控制外部设备等能力（Shi et al., 2025）。形式化地，LLM智能体A可以定义为一个元组：

$$A = \{LLM, T, P, M\}$$

其中：
- $LLM$ 是认知引擎
- $T = \{\tau_1, ..., \tau_n\}$ 是一组外部工具，每个工具具有明确定义的功能
- $P$ 表示构造成LLM推理过程和工具使用策略的提示
- $M$ 是用于存储历史交互、状态和上下文信息的记忆模块（Zhang et al., 2024）

LLM智能体的操作范式通常是推理、行动和观察的迭代循环。智能体评估给定目标，制定计划，执行动作（通常通过调用工具），然后结合所得结果反馈指导下一步。这个循环一直持续到任务完成，使LLM智能体能够解构和解决复杂的多步骤问题。

**多智能体系统**。基于单个LLM智能体的能力，多智能体系统（MAS）代表了协作AI的下一个前沿。MAS由多个自主智能体在共享环境中运行，经过协调来处理单个智能体无法有效处理的过于复杂或范围过大的目标（Guo et al., 2024）。通过结构化交互和角色专业化，这些智能体可以涌现出智能和协同效应。形式化地，MAS可以描述为：

$$MAS = S(A_1, A_2, \cdots, A_m)$$

其中每个$A_i$是如前所述的LLM智能体，$S$表示指导智能体交互的协作框架。该框架定义了智能体角色、通信协议和潜在的层次结构。

基于LLM的MAS的一个定义特征是使用自然语言作为智能体间通信的主要媒介。与传统的刚性编码协议相比，这提供了前所未有的灵活性。然而，这也给保持语义一致性、确保目标一致性和管理复杂对话流带来了重大挑战。因此，有效协作结构$S$的设计对系统性能至关重要，仍然是一个活跃的研究领域，这也引出了我们在本文中要解决的挑战。

**研究动机**。在当前的MAS研究和应用中，广泛采用的协调结构$S$是计划-执行框架（Huang et al., 2024）。该框架为智能体分配专门角色，通常是规划者或执行者。工作流一般分为三个不同阶段展开：

(1) **全局规划**：规划智能体分析请求并将其分解为结构化子任务；
(2) **任务分配**：根据智能体预先定义的能力将子任务分配给执行智能体；
(3) **执行与反馈**：执行器完成分配的任务并报告结果。

尽管这种范例为多智能体协作提供了结构化方法，但它在复杂动态任务中仍存在困难。规划和执行的严格分离通常导致次优性能，特别是在任务需求可能在执行过程中发生变化的环境中。我们的工作受到该模型固有的三个关键挑战的推动：

- **僵化的计划执行**。传统计划通常是静态的。一旦制定，规划者通常必须等待所有执行器完成报告才能聚合结果。然而，单个执行器的自主性意味着它们的动作可能偏离规定计划，导致不完整或冗余工作。这种偏离为规划者提供了不可靠的反馈，最终降低了整体系统性能（Cemri et al., 2025）。

- **静态智能体能力**。计划-执行模型预设智能体的预定义能力足以应对所有预期任务。这个假设在实践中经常被打破。例如，对智能体技能的不准确或不完整描述可能导致规划者做出次优任务分配（Shen et al., 2023）。此外，系统无法适应需要新工具或能力的不可预见任务，从而限制了其在新问题上的可扩展性和性能。

- **低效通信**。智能体之间的信息交接经常成为瓶颈。关键上下文可能在任务委派过程中丢失或失真，阻碍无缝执行（Yan, 2025）。这个问题因缺乏共享状态管理系统而更加严重。智能体通常在对整体进度不完整的视图下操作，因为状态更新通常仅在任务完成时才聚合。这种缺乏实时共享感知的情况可能导致冗余工作和关键延迟。

这些挑战共同限制了现有多智能体系统的有效性和适应性（Cemri et al., 2025）。克服这些限制需要更先进的框架，实现灵活执行、动态智能体角色和可靠的上下文感知通信。

---

## 3 Aime 概述

Aime是一个新颖的多智能体系统，将传统的静态计划-执行范例转变为动态、响应式的规划和执行。它基于**动态适应**原则运行，其中任务分配和智能体能力都根据实时执行反馈和进度更新进行演变。

### 3.1 框架

Aime框架由四个协同工作的核心组件组成，实现动态多智能体协作：

**图1：Aime框架的工作流**

- **动态规划器**（Dynamic Planner）。动态规划器作为任务管理的中心协调器。它将高级目标分解为可执行子任务的层次结构，并维护全局任务列表来跟踪每个子任务的状态。它持续监控执行进度，并根据动态Actor的反馈和进度管理模块的状态更新动态调整计划。

- **Actor工厂**（Actor Factory）。Actor工厂负责实例化针对特定子任务需求量身定制的专门Actor。收到子任务后，工厂分析其规范以确定Actor的最佳配置。这个过程包括选择合适的角色、相关知识库和必要的工具集。然后工厂使用定制提示和系统配置组装Actor，确保每个Actor都专为其分配的任务构建。

- **动态Actor**（Dynamic Actor）。动态Actor是自主智能体，执行由动态规划器分配的特定子任务。每个Actor采用ReAct框架（Yao et al., 2023），通过"推理"和"行动"的迭代循环运行。在每个循环中，Actor从预配置工具包中选择最合适的工具，执行动作，然后根据结果观察评估结果。这个循环一直持续到满足子任务的完成标准。

- **进度管理模块**（Progress Management Module）。进度管理模块用作共享记忆和全系统协调的中心状态。它维护整个任务层次结构和所有子任务实时状态的结构化表示。这种集中记录确保动态规划器和所有Actor对进度有一致理解。至关重要的是，通过在每个任务条目中嵌入明确的完成标准，该模块为验证任务完成提供了清晰客观的标准。

### 3.2 工作流

Aime框架通过迭代工作流运行，协调其组件之间的动态协作。如图1所示，过程从用户请求开始，经过规划、Actor实例化、执行和状态更新的循环，详细说明如下：

**步骤1：任务分解**。工作流在动态规划器收到用户任务时开始。规划器将请求分解为结构化的子任务计划，并在进度管理模块中初始化相应的任务列表。

**步骤2：(子)任务分派**。然后动态规划器从计划中识别下一个可执行子任务，并将其规范分派给Actor工厂。

**步骤3：Actor实例化**。收到子任务规范后，Actor工厂实例化专门的动态Actor。该Actor专为子任务构建，配备有效执行所需的精确角色、知识和工具。

**步骤4：ReAct执行**。新实例化的Actor通过遵循ReAct范式执行分配的子任务。它在推理和行动的循环中运行，从工具包调用工具，向子任务目标逐步推进。

**步骤5：进度更新**。执行期间，Actor持续向进度管理模块报告状态更新。这确保全局任务状态保持同步，对所有组件（特别是动态规划器）可用。

**步骤6：评估与迭代**。子任务完成后，Actor向动态规划器报告最终结果。规划器评估结果，更新全局计划，然后返回步骤2分派下一个可用子任务。这个循环重复直到顶级用户请求成功完成。

这种集成工作流直接解决了多智能体协作中的几个关键挑战。动态规划和分派循环（步骤2和6）确保了上下文感知任务分配，克服了静态预定义计划的刚性。集中式进度管理模块（步骤1和5）提供了任务状态的单一真值来源，确保高效信息共享并减少通信开销。最后，即时Actor实例化（步骤3）允许灵活的角色定义，创建精确适应任务的Actor，这与固定Actor角色的系统不同。

---

## 4 方法论

本节详细介绍Aime框架的核心组件：动态规划器（4.1节）、Actor工厂（4.2节）和动态Actor（4.3节）。然后我们解释这些组件如何通过进度管理模块（4.4节）交互，该模块作为中心协调枢纽。

### 4.1 动态规划器

动态规划器旨在解决传统计划-执行框架固有的执行刚性问题。在这类框架中，规划器通常一直空闲直到所有子任务完成，导致适应瓶颈。相比之下，我们的动态规划器整合了高级战略概述和自适应增量执行。这种双重焦点允许系统在保持对最终目标清晰路线的同时，保持对执行动态的响应能力。

在其核心，规划器管理两个操作层面：维护全局任务结构和确定即时下一步行动。我们将这种双重责任形式化为单个迭代推理步骤。给定总体目标$G$，在每一步$t$，规划器（表示为智能体$A_{\text{planner}}$）评估当前任务列表$L_t$和历史结果$H_t = \{o_1, ..., o_t\}$。其操作由函数定义：

$$(L_{t+1}, g_{t+1}) = \text{LLM}_{\text{planner}}(P_{\text{planner}}, (G, L_t, H_t)) \tag{1}$$

规划器在每次迭代中产生两个输出：

- $L_{t+1}$ 是更新后的全局任务列表。这反映了规划器基于新信息对任务层次结构的修正理解，即战略性或"大步骤"输出。如果不需要重大战略改变，$L_{t+1}$可以简单地复制$L_t$并更新任务状态。

- $g_{t+1}$ 是系统下一步要执行的特定可操作动作。这是战术性或"小步骤"输出，例如向Actor工厂分派子任务。

这种公式化带来了非凡的适应性。例如，如果子任务失败，规划器可以在单次迭代中同时进行战略和战术调整。其战略推理可能修改全局计划$L_{t+1}$以包含新的应急子任务。同时，其战术决策$g_{t+1}$将分派这个新子任务立即执行。这种规划和重新规划的无缝整合是我们方法的一个关键优势。

规划器与系统状态的交互严格由进度管理模块维护的结构化任务列表$L$介导。这种纪律性方法确保整个系统的状态一致性。通过保持全局规划和即时行动之间的动态平衡，动态规划器成为Aime在复杂多变环境中弹性和有效性的基石。

### 4.2 Actor工厂

为了克服预定义智能体角色的限制，Aime引入了Actor工厂，这个组件实现了我们称之为**动态Actor实例化**的机制。不是从固定的通用智能体池中选择，工厂按需组装专门的Actor，根据给定子任务$g_t$的确切需求量身定制。

从动态规划器接收到子任务$g_t$后，工厂分析其规范以确定必要的能力。然后它通过从精选组件池中选择和组合来构造新Actor$A_t$：

$$A_t = F_{\text{factory}}(g_t) \quad \text{where} \quad A_t = \{LLM_t, T_t, P_t, M_t\} \tag{2}$$

工厂的主要功能是选择专用工具包$T_t$并构造定制化系统提示$P_t$。

**工具包选择**。复杂MAS中的一个重大挑战是管理大量多样化的工具。向智能体的LLM展示所有可用工具会导致低效选择或错误。为了缓解这个问题，Aime将工具组织为预先打包的捆绑包，每个捆绑包对应特定功能类别（例如，"网页搜索"捆绑包、"文件系统"捆绑包）。工厂选择适当的捆绑包形成最终工具包$T_t$，而不是从单个工具的扁平列表中挑选。这种基于捆绑包的方法确保功能完整性并降低关键工具遗漏的风险。

**提示生成**。系统提示$P_t$由几个模块化组件动态组装，为Actor创建精确的操作上下文：

$$P_t = \text{Compose}(\rho_t, \text{desc}(T_t), \kappa_t, \varepsilon, \Gamma) \tag{3}$$

其中组件包括：

- **角色**（$\rho_t$）。定义Actor的专业角色和专长（例如，"擅长创造独特难忘旅程的专家旅行规划师"）。角色生成与子任务$g_t$对齐，有效创建专门的专家。

- **工具描述**（$\text{desc}(T_t)$）。提供所选工具包$T_t$的简明文本描述。提供最小且充足的工具集缩小了LLM的决策空间，提高了焦点和性能。

- **知识**（$\kappa_t$）。由从知识库动态检索的高度相关信息组成，支持子任务。对于旅行规划任务，这可能包括识别当地景点的提示。

- **环境**（$\varepsilon$）。提供全局上下文，例如操作系统细节或系统范围约束（例如，当前时间、访问权限），确保Actor的动作具有环境感知。

- **格式**（$\Gamma$）。指定所需的输出结构（例如，JSON模式），确保Actor的响应可以可靠地解析以进行自动处理和状态更新。

**总结**。这种即时实例化机制与静态智能体角色系统相比提供了两个明显优势。首先，它为Actor配备了任务所需的确切能力，消除了能力缺口和无关工具的认知负担。其次，它增强了系统可扩展性；只需添加新工具捆绑包或知识模块即可引入新能力，而无需重新设计和重新验证大量静态智能体原型的昂贵过程。

### 4.3 动态Actor

一旦由Actor工厂实例化，动态Actor作为自主智能体运行，专门致力于执行分配的子任务$g_t$。其行为由ReAct范式管理（Yao et al., 2023），该范式将推理和行动整合到迭代执行循环中。

Actor $A_t$通过重复调用其核心LLM来执行子任务。在内部循环的每一步$k$，Actor分析其目标和局部历史以生成新想法$thought_{k+1}$和后续动作$action_{k+1}$。这个过程形式化为：

$$(thought_{k+1}, action_{k+1}) = \text{LLM}_t(P_t, (g_t, H_k)) \tag{4}$$

其中$H_k$是存储在Actor局部记忆$M_t$中的先前（动作，观察）对序列。这个循环通过三个不同阶段展开：

- **推理**。Actor反思子任务目标、过去动作和得到的观察，为下一个即时步骤制定计划。

- **行动**。基于推理，Actor选择并执行一个动作，通常是从其专门工具包$T_t$中调用工具。

- **观察**。Actor接收执行工具的输出。这个新观察被追加到其历史$H_k$中，并作为下一推理阶段的关键上下文。

动态Actor的一个关键特征是它能够主动报告进度。为了促进这一点，Actor的工具包$T_t$增强了一个特殊的系统提供工具：`Update Progress(status, message)`。至关重要的是，调用此工具的决定不是硬编码的；相反，Actor的LLM自主确定适当的报告时机，例如在完成重要里程碑或遇到障碍后。这种机制为动态规划器提供了近乎实时的正在进行的活动视图，而不会中断Actor的主要工作流。

当满足子任务的完成标准时，执行循环终止。此时，Actor为动态规划器生成最终的结构化报告$o_t$。该报告包括结果的结论性总结、最终状态更新以及后续任务所需的任何相关工件（例如，文件路径、数据输出）。

### 4.4 进度管理模块

多智能体系统中的一个核心挑战是保持一致且全局统一的任务进度理解。进度管理模块通过作为框架的集中状态管理器解决了这个问题，为整个任务层次结构建立了单一真值来源。这确保动态规划器和所有动态Actor在共享、统一的系统状态视图下操作。

#### 4.4.1 核心数据结构：进度列表

该模块的基石是全局可访问的层次化数据结构，我们称之为**进度列表**，记为$L$。它表示完整的任务分解，从高级目标到细致的子任务。典型实现使用人类可读和机器可解析的格式，如Markdown任务列表：

```
- 目标1：进行初步研究
  - [x] 子目标1.1：研究热门景点
  - [x] 子目标1.2：调查交通选择
- 目标2：确定行程和预算
  - [ ] 子目标2.1：研究酒店住宿
  - [ ] 子目标2.2：计算总预估预算
  - [ ] 子目标2.3：创建最终行程文档
```

进度列表的关键特征：

- **实时状态跟踪**。每个项目都标记有当前状态（例如，已完成`[x]`，待处理`[ ]`），提供全系统进度的概览。

- **嵌入式上下文和依赖关系**。层次结构隐式编码了任务之间的依赖关系。此外，每个项目可以嵌入或链接到明确的完成标准，提供验证的客观标准。

#### 4.4.2 通过进度更新进行协调

规划器和Actor之间的协调通过针对进度列表的两种通信协议实现：执行期间的实时同步和任务完成时的结构化结论。

**实时同步**。如第4.3节所述，每个动态Actor可以通过调用`Update Progress`工具自主报告增量进度。这个动作将更新推送到进度列表，允许Actor在整个子任务完成前发出关键里程碑（例如，"已筛选出东京三个潜在酒店"）的信号或标记问题（例如，"目标日期的直航班机已全部订满"）。这种机制为动态规划器提供了高保真、近乎实时的正在进行的活动可见性，实现更主动和明智的决策。

**结构化任务结论**。当Actor$A_t$完成分配的子任务时，它使用标准化结论报告$o_t$向动态规划器传达最终结果。该消息触发全局状态的正式更新，规划器使用它来修改进度列表。最终报告$o_t$是由三个基本部分组成的结构化载荷：

- **状态更新**。对进度列表中分配项目的明确更新，将它们标记为已完成或失败。

- **结论总结**。任务执行的叙述性总结。这包括最终结果、遇到的障碍和关键见解，提供简单成功/失败标记之外的丰富上下文。

- **引用指针**。任务执行期间产生的关键工件指针的结构化集合（例如，文件、数据库记录ID、URL），确保输出可追踪且可供后续任务访问。

通过将共享数据结构与双重通信协议（一个用于实时更新，一个用于最终结论）相结合，进度管理模块确保在整个任务生命周期中明确维护、准确更新和高效传输上下文。这为动态多智能体协作奠定了坚实的基础。

---

## 5 实验

为了评估我们提出框架的有效性，我们在三个多样且具有挑战性的基准上进行了一系列实验。

### 5.1 实验设置

**数据集**。我们选择了三个基准，代表广泛的复杂多步骤自主智能体任务：

- **GAIA**（Mialon et al., 2024）是通用AI助手的挑战性基准，包含需要多步推理、工具使用和多模态内容理解的问题。我们使用官方精确字符串匹配指标在公开测试集上进行评估。

- **SWE-bench Verified**（Jimenez et al., 2024）是SWE-bench的精选子集，用于评估智能体解决现实世界软件工程问题的能力。通过运行单元测试严格评估成功，确保提供的修复正确且不引入回归。

- **WebVoyager**（He et al., 2024）是网络智能体与真实网站交互的端到端基准。性能通过15个现实网站上的任务成功率衡量。

**基线**。我们将Aime与每个领域最先进的专门基线进行比较。为了确保公平比较，在适用情况下，所有智能体（包括我们的）都由相同的基础LLM驱动。

- 在GAIA上，我们与领先的通用智能体框架比较：Langfun、Trase和OWL（Hu et al., 2025）。

- 在SWE-bench Verified上，我们的基线是顶级性能代码智能体：SWE-agent（Yang et al., 2024）和OpenHands（Wang et al., 2025）。

- 在WebVoyager上，我们与著名网络智能体比较：Browseruse（Müller & Žunič, 2024）、Operator（OpenAI, 2025）和Skyvern（Skyvern, 2025）。

### 5.2 实验结果

表1展示了主要实验结果，将Aime与各个基准上最先进的专门智能体进行比较。数据清楚地表明，我们的框架不仅能够竞争，而且始终优于这些高度调优的系统，确立了其强大的泛化能力并在这些不同领域建立了新的先进水平。

**表1：Aime与三个基准上专门基线的性能比较。基线仅在其目标领域评估，而Aime在所有三个领域评估。每列的最佳分数以粗体显示。**

| 模型 | GAIA<br>(成功率%) | SWE-bench Verified<br>(解决率%) | WebVoyager<br>(成功率%) |
|------|-----------------|-------------------------------|------------------------|
| **通用智能体** | | | |
| Langfun | 71.5 | - | - |
| Trase | 70.3 | - | - |
| OWL | 69.1 | - | - |
| **软件工程智能体** | | | |
| SWE-agent | - | 62.4 | - |
| OpenHands | - | 65.8 | - |
| **网页导航智能体** | | | |
| Browseruse | - | - | 89.1 |
| Operator | - | - | 87 |
| Skyvern | - | - | 85.6 |
| **Aime (本文)** | **77.6** | **66.4** | **92.3** |

在GAIA上，Aime达到了77.6%的最新成功率，优于最强基线Langfun。我们将这种显著的性能提升归功于动态规划器，它允许系统在初始推理路径失败时灵活调整策略，这是GAIA复杂多步问题的关键能力。

在SWE-bench Verified上，Aime解决了66.4%的问题，超过了OpenHands等顶级专门智能体。尽管该领域领先智能体的性能已经很有竞争力，但我们相信我们的优势来自Actor工厂。它可以动态实例化不同类型的智能体（例如，先使用"代码阅读器"理解上下文，再使用"调试器"定位错误），从而带来更稳健有效的问题解决过程。

在WebVoyager上，Aime在真实网络环境中展示了卓越的鲁棒性，达到了令人印象深刻的92.3%成功率。这种性能超过了Browseruse等强大基线。与可能因意外网站变化而失败的固定计划智能体不同，Aime在动态Actor和动态规划器之间紧密反馈循环使其能够立即重新规划并从错误中恢复，从而带来更高的任务完成率。

---

## 6 相关工作

多智能体系统（MAS）领域因大语言模型（LLM）的崛起而发生了变革（Brown et al., 2020; OpenAI, 2023）。与传统依赖刚性正式规划模型的系统不同（Ghallab et al., 2004; Rao & Georgeff, 1995），现代MAS利用LLM作为认知引擎，通过自然语言实现前所未有的灵活性和协调性。这刺激了新协作范式的发展，我们在下文回顾。

### 6.1 基于角色的多智能体协作

基于角色的协作是现代基于LLM的MAS中的主导范式，即为智能体分配专门角色以分解复杂任务，这通常受到人类组织结构的启发。像MetaGPT（Hong et al., 2024）和ChatDev（Qian et al., 2024）这样的框架模拟软件公司，扮演"产品经理"或"工程师"角色的智能体遵循结构化协议实现目标。类似地，MAGIS（Tao et al., 2024）和MarsCode Agent（Liu et al., 2024）为软件开发设计专门的标准操作程序（SOP）。CodeR（Chen et al., 2024）通过预定义多个SOP并根据当前任务选择一个扩展了这种方法。

尽管这些系统展示了结构化协作的能力，但它们的工作流和智能体能力大多是静态的。这种刚性限制了它们适应不可预见情况或偏离预定义SOP任务的能力。像AutoGen（Wu et al., 2023）和AgentVerse（Chen et al., 2023）这样的其他框架提供了更灵活的通信模式，但智能体角色及其能力的定义通常仍然是固定的。

### 6.2 自动化智能体架构设计

认识到静态设计的局限性，最近的研究线专注于自动搜索最优智能体架构。然而，这些方法通常旨在在执行开始前找到优越的静态设计。

- **工作流优化**：一些工作旨在自动生成协作计划本身。例如，AOP（Li et al., 2025）研究了一种面向智能体的规划方法，利用快速任务分解和奖励模型进行高效评估。其他工作，如AFlow（Zhang et al., 2025b）和Flow（Niu et al., 2025）自动生成基于图的工作流，尽管通常采用同质智能体能力的简化假设。更高级的方法如Agentic Supernet（Zhang et al., 2025a）和FlowReasoner（Gao et al., 2025）甚至学习从预定义智能体算子生成这些工作流。然而，一个共同的局限性是，这些方法在执行之前生成静态协作计划，使得它们容易受到偏离初始策略的实时事件影响。

- **智能体角色优化**：补充研究专注于优化单个智能体设计。AgentSquare（Shang et al., 2025）通过从给定模块集合组合来搜索最优智能体架构，而ADAS（Hu et al., 2024）通过代码生成自动化单个智能体的创建。这些方法增强了智能体组件，但不直接解决多智能体协作的动态性。

与这些方法相比，Aime提供了执行期间动态适应的框架。它结合了基于实时结果不断改进计划的动态规划器和实现按需组装专门智能体的Actor工厂。这种将响应式规划与即时专业化相结合的方法提供了一种实用且有弹性的适应性解决方案，避免了离线架构搜索的高计算开销。

---

## 7 结论

本文介绍了Aime，一个新颖的框架，通过三项关键创新实现动态响应式协作：用于自适应策略的动态规划器、用于按需实例化专门智能体的Actor工厂，以及用于实现连贯状态感知的集中式进度管理模块。它专门设计用于解决传统计划-执行框架的关键弱点，即僵化规划、静态智能体角色和低效通信。我们的实验证实，这种方法非常有效，Aime在适应性、效率和整体任务成功率方面显著优于传统模型。

未来工作将重点增强大型智能体团队的可扩展性，并赋予智能体自主获取新能力，减少对预策划工具的依赖。通过将范式从静态执行转变为动态适应，Aime向着构建更具弹性和智能的自主系统迈出了重要一步。

---

## 参考文献

- Tom Brown, Benjamin Mann, Nick Ryder, Melanie Subbiah, Jared D Kaplan, Prafulla Dhariwal, Arvind Neelakantan, Pranav Shyam, Girish Sastry, Amanda Askell, Sandhini Agarwal, Ariel Herbert-Voss, Gretchen Krueger, Tom Henighan, Rewon Child, Aditya Ramesh, Daniel Ziegler, Jeffrey Wu, Clemens Winter, Chris Hesse, Mark Chen, Eric Sigler, Mateusz Litwin, Scott Gray, Benjamin Chess, Jack Clark, Christopher Berner, Sam McCandlish, Alec Radford, Ilya Sutskever, and Dario Amodei. 语言模型是少样本学习者。*Neural Information Processing Systems (NeurIPS)*，第33卷，1877–1901页。Curran Associates, Inc.，2020。

- Mert Cemri, Melissa Z. Pan, Shuyi Yang, Lakshya A. Agrawal, Bhavya Chopra, Rishabh Tiwari, Kurt Keutzer, Aditya G. Parameswaran, Dan Klein, Kannan Ramchandran, Matei Zaharia, Joseph E. Gonzalez, and Ion Stoica. 为什么多智能体LLM系统会失败？ArXiv预印本，arXiv:2503.13657，2025。

- Yupeng Chang, Xu Wang, Jindong Wang, Yuan Wu, Linyi Yang, Kaijie Zhu, Hao Chen, Xiaoyuan Yi, Cunxiang Wang, Yidong Wang, Wei Ye, Yue Zhang, Yi Chang, Philip S. Yu, Qiang Yang, and Xing Xie. 大语言模型评估综述。*ACM Transactions on Intelligent Systems and Technology*，15(3):39:1–39:45，2024。

- Dong Chen, Shaoxin Lin, Muhan Zeng, Daoguang Zan, Jian-Gang Wang, Anton Cheshkov, JunSun, Hao Yu, Guoliang Dong, Artem Aliev, Jie Wang, Xiao Cheng, Guangtai Liang, Yuchi Ma, Pan Bian, Tao Xie, and Qianxiang Wang. CodeR：基于多智能体和任务图的问题解决。ArXiv预印本，arXiv:2406.01304，2024。

- Weize Chen, Yusheng Su, Jingwei Zuo, Cheng Yang, Chenfei Yuan, Chen Qian, Chi-Min Chan, Yujia Qin, Yaxi Lu, Ruobing Xie, Zhiyuan Liu, Maosong Sun, and Jie Zhou. AgentVerse：促进多智能体协作并探索智能体的涌现行为。ArXiv预印本，arXiv:2308.10848，2023。

- Hongcheng Gao, Yue Liu, Yufei He, Longxu Dou, Chao Du, Zhijie Deng, Bryan Hooi, Min Lin, and Tianyu Pang. FlowReasoner：强化查询级元智能体。ArXiv预印本，arXiv:2504.15257，2025。

- Malik Ghallab, Dana S. Nau, and Paolo Traverso. 自动化规划——理论与实践。Elsevier，2004。ISBN 978-1-55860-856-6。

- Taicheng Guo, Xiuying Chen, Yaqi Wang, Ruidi Chang, Shichao Pei, Nitesh V. Chawla, Olaf Wiest, and Xiangliang Zhang. 基于大语言模型的多智能体：进展与挑战综述。*Proceedings of the 23rd International Joint Conference on Artificial Intelligence (IJCAI)*，8048–8057页。ijcai.org，2024。

- Hongliang He, Wenlin Yao, Kaixin Ma, Wenhao Yu, Yong Dai, Hongming Zhang, Zhenzhong Lan, and Dong Yu. WebVoyager：使用大型多模态模型构建端到端网络智能体。*Proceedings of the 62nd Annual Meeting of the Association for Computational Linguistics (ACL)*，6864–6890页。Association for Computational Linguistics，2024。

- Sirui Hong, Mingchen Zhuge, Jonathan Chen, Xiawu Zheng, Yuheng Cheng, Jinlin Wang, Ceyao Zhang, Zili Wang, Steven Ka Shing Yau, Zijuan Lin, Liyang Zhou, Chenyu Ran, Lingfeng Xiao, Chenglin Wu, and Jürgen Schmidhuber. MetaGPT：多智能体协作的元编程。*The 12th International Conference on Learning Representations (ICLR)*。OpenReview.net，2024。

- Mengkang Hu, Yuhang Zhou, Wendong Fan, Yuzhou Nie, Bowei Xia, Tao Sun, Ziyu Ye, Zhaoxuan Jin, Yingru Li, Qiguang Chen, Zeyu Zhang, Yifeng Wang, Qianshuo Ye, Bernard Ghanem, Ping Luo, and Guohao Li. OWL：通用多智能体辅助的优化工作力学习。ArXiv预印本，arXiv:2505.23885，2025。

- Shengran Hu, Cong Lu, and Jeff Clune. 智能体系统的自动化设计。ArXiv预印本，arXiv:2408.08435，2024。

- Xu Huang, Weiwen Liu, Xiaolong Chen, Xingmei Wang, Hao Wang, Defu Lian, Yasheng Wang, Ruiming Tang, and Enhong Chen. 理解LLM智能体的规划综述。ArXiv预印本，arXiv:2402.02716，2024。

- Carlos E. Jimenez, John Yang, Alexander Wettig, Shunyu Yao, Kexin Pei, Ofir Press, and Karthik R. Narasimhan. SWE-bench：语言模型能否解决GitHub上的现实世界问题？*The 12th International Conference on Learning Representations (ICLR)*。OpenReview.net，2024。

- Ao Li, Yuexiang Xie, Songze Li, Fugee Tsung, Bolin Ding, and Yaliang Li. 多智能体系统中的面向智能体规划。*The 13th International Conference on Learning Representations (ICLR)*。OpenReview.net，2025。

- Yizhou Liu, Pengfei Gao, Xinchen Wang, Jie Liu, Yexuan Shi, Zhao Zhang, and Chao Peng. MarsCode Agent：原生AI自动化错误修复。ArXiv预印本，arXiv:2409.00899，2024。

- Grégoire Mialon, Clémentine Fourrier, Thomas Wolf, Yann LeCun, and Thomas Scialom. GAIA：通用AI助手基准。*The 12th International Conference on Learning Representations (ICLR)*。OpenReview.net，2024。

- Magnus Müller and Gregor Žunič. Browser use：让AI控制你的浏览器，2024。URL https://github.com/browser-use/browser-use。

- Boye Niu, Yiliao Song, Kai Lian, Yifan Shen, Yu Yao, Kun Zhang, and Tongliang Liu. Flow：模块化智能体工作流自动化。*The 13th International Conference on Learning Representations (ICLR)*。OpenReview.net，2025。

- OpenAI. GPT-4技术报告。ArXiv预印本，arXiv:2303.08774，2023。

- OpenAI. Introducing operator，2025。URL https://openai.com/index/introducing-operator。

- Chen Qian, Wei Liu, Hongzhang Liu, Nuo Chen, Yufan Dang, Jiahao Li, Cheng Yang, Weize Chen, Yusheng Su, Xin Cong, Juyuan Xu, Dahai Li, Zhiyuan Liu, and Maosong Sun. ChatDev：软件开发的交流智能体。*Proceedings of the 62nd Annual Meeting of the Association for Computational Linguistics (ACL)*，15174–15186页。Association for Computational Linguistics，2024。

- Yujia Qin, Shihao Liang, Yining Ye, Kunlun Zhu, Lan Yan, Yaxi Lu, Yankai Lin, Xin Cong, Xiangru Tang, Bill Qian, Sihan Zhao, Lauren Hong, Runchu Tian, Ruobing Xie, Jie Zhou, Mark Gerstein, Dahai Li, Zhiyuan Liu, and Maosong Sun. ToolLLM：促进大语言模型掌握16000+真实世界API。*The 12th International Conference on Learning Representations (ICLR)*。OpenReview.net，2024。

- Anand S. Rao and Michael P. Georgeff. BDI智能体：从理论到实践。*Proceedings of the 1st International Conference on Multiagent Systems*，312–319页。The MIT Press，1995。

- Yu Shang, Yu Li, Keyu Zhao, Likai Ma, Jiahe Liu, Fengli Xu, and Yong Li. AgentSquare：模块化设计空间中的自动LLM智能体搜索。*The 13th International Conference on Learning Representations (ICLR)*。OpenReview.net，2025。

- Yongliang Shen, Kaitao Song, Xu Tan, Dongsheng Li, Weiming Lu, and Yueting Zhuang. HuggingGPT：使用ChatGPT和Hugging Face中的工具解决AI任务。*Advances in Neural Information Processing Systems (NeurIPS)*，第36卷，38154–38180页。Curran Associates, Inc.，2023。

- Zhengliang Shi, Shen Gao, Lingyong Yan, Yue Feng, Xiuyi Chen, Zhumin Chen, Dawei Yin, Suzan Verberne, and Zhaochun Ren. 野外工具学习：赋予语言模型作为自动工具智能体能力。*Proceedings of the ACM on Web Conference (WWW)*，2222–2237页。ACM，2025。

- Skyvern. 使用LLM和计算机视觉自动化浏览器工作流，2025。URL https://www.skyvern.com/。

- Wei Tao, Yucheng Zhou, Yanlin Wang, Wenqiang Zhang, Hongyu Zhang, and Yu Cheng. MAGIS：基于LLM的多智能体框架用于GitHub问题解决。*Advances in Neural Information Processing Systems (NeurIPS)*，第37卷，51963–51993页。Curran Associates, Inc.，2024。

- Guanzhi Wang, Yuqi Xie, Yunfan Jiang, Ajay Mandlekar, Chaowei Xiao, Yuke Zhu, Linxi Fan, and Anima Anandkumar. Voyager：使用大语言模型的开放式具身智能体。*Transactions on Machine Learning Research*，2024，2024a。

- Lei Wang, Chen Ma, Xueyang Feng, Zeyu Zhang, Hao Yang, Jingsen Zhang, Zhiyuan Chen, Jiakai Tang, Xu Chen, Yankai Lin, Wayne Xin Zhao, Zhewei Wei, and Jirong Wen. 基于大语言模型的自主智能体综述。*Frontiers of Computer Science*，18(6):186345，2024b。

- Xingyao Wang, Boxuan Li, Yufan Song, Frank F. Xu, Xiangru Tang, Mingchen Zhuge, Jiayi Pan, Yueqi Song, Bowen Li, Jaskirat Singh, Hoang H. Tran, Fuqiang Li, Ren Ma, Mingzhang Zheng, Bill Qian, Yanjun Shao, Niklas Muennighoff, Yizhe Zhang, Binyuan Hui, Junyang Lin, and et al. OpenHands：面向AI软件开发人员的开放平台作为通用智能体。*The 13th International Conference on Learning Representations (ICLR)*。OpenReview.net，2025。

- Qingyun Wu, Gagan Bansal, Jieyu Zhang, Yiran Wu, Shaokun Zhang, Erkang Zhu, Beibin Li, Li Jiang, Xiaoyun Zhang, and Chi Wang. AutoGen：通过多智能体对话框架启用下一代LLM应用。ArXiv预印本，arXiv:2308.08155，2023。

- Walden Yan. Cognition博客：不要构建多智能体，2025。URL https://cognition.ai/blog/dont-build-multi-agents。

- John Yang, Carlos E. Jimenez, Alexander Wettig, Kilian Lieret, Shunyu Yao, Karthik Narasimhan, and Ofir Press. SWE-agent：智能体-计算机接口实现自动化软件工程。*Advances in Neural Information Processing Systems (NeurIPS)*，第37卷，50528–50652页。Curran Associates, Inc.，2024。

- Shunyu Yao, Jeffrey Zhao, Dian Yu, Nan Du, Izhak Shafran, Karthik R. Narasimhan, and Yuan Cao. ReAct：在语言模型中协同推理和行动。*The 11th International Conference on Learning Representations (ICLR)*。OpenReview.net，2023。

- Guibin Zhang, Luyang Niu, Junfeng Fang, Kun Wang, Lei Bai, and Xiang Wang. 通过智能体超网进行多智能体架构搜索。ArXiv预印本，arXiv:2502.04180，2025a。

- Jiayi Zhang, Jinyu Xiang, Zhaoyang Yu, Fengwei Teng, Xionghui Chen, Jiaqi Chen, Mingchen Zhuge, Xin Cheng, Sirui Hong, Jinlin Wang, Bingnan Zheng, Bang Liu, Yuyu Luo, and Chenglin Wu. AFlow：自动化智能体工作流生成。*The 13th International Conference on Learning Representations (ICLR)*。OpenReview.net，2025b。

- Zeyu Zhang, Xiaohe Bo, Chen Ma, Rui Li, Xu Chen, Quanyu Dai, Jieming Zhu, Zhenhua Dong, and Ji-Rong Wen. 基于大语言模型智能体的记忆机制综述。ArXiv预印本，arXiv:2404.13501，2024。

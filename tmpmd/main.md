OD Prediction Method based on EnvTree-Guided Semantic Random Walk and Hierarchical Memory

Zhao Tian1,2, Shaochen Yu1,2 ,HaoBo Zhang1,2, Qiaosen Li1,2, Yanfang Yang3,4, Wei She1,2 and Wei Liu1,2 (\*)

1 School of Cyber Science and Engineering, Zhengzhou University, Zhengzhou 450000, China

2 Zhengzhou Key Laboratory of Blockchain and Data Intelligence, Zhengzhou 450000, China

3 China Academy of Transportation Sciences, Beijing 100029, China

4 Key Laboratory of Transport Industry of Big Data Application Technologies for Comprehensive Transport, Beijing 100029, China

wliu@zzu.edu.cn

**Abstract.** Origin-Destination (OD) demand prediction is critical in intelligent transportation systems, helping alleviate congestion and optimize traffic. However, current methods respond poorly to complex patterns and unexpected events, often causing inaccurate predictions. Their reliance on fixed-interval time slots also limits the capture of multi-scale traffic dynamics. To address these issues, we propose an environment tree-guided semantic random walk, introducing semantic similarity constraints into node transitions. This lets node embeddings capture both topological and semantic information for improved cross-regional traffic modeling. Our hierarchical memory system integrates continuous, discrete, and reflective memory for unified, multi-scale representations of short-term dynamics, long-term patterns, and semantic context. Based on this, we present an OD prediction method, ETSRW-HM (EnvTree-Guided Semantic Random Walk and Hierarchical Memory). Experiments show our model surpasses mainstream baselines in RMSE and PCC metrics (1.5327 and 0.8611), demonstrating greater accuracy and trend prediction.

**Keywords:** Dynamic Graph Neural Networks, Random Walk, Hierarchical Memory, OD Prediction.

1. Introduction

As the lifeline of modern cities, the stable operation of urban transportation systems has a decisive impact on socioeconomic development.

With the advancement of traffic sensing technologies and urban big data platforms, massive high-frequency spatiotemporal trajectory data lays a core data foundation for the research on Origin-Destination (OD) prediction in Intelligent Transportation Systems (ITS).

Recent research from the International Transport Forum (ITF) [1–4] shows that traffic congestion and traffic accidents cause annual economic losses accounting for 2–4% of urban GDP. The drastic fluctuations in OD distribution induced by such events markedly increase the difficulty of prediction. Accurate OD prediction acts as a fundamental prerequisite for traffic scheduling and optimization in smart cities.

To address complex spatiotemporal dependencies in OD prediction, researchers have proposed various deep learning-based methods. However, existing research still faces several key unsolved problems:

1. Existing models for inter-node relations often lack semantic distinction and dynamic adaptability. Many methods infer node associations solely from historical flow. They ignore behavioral differences across semantic roles (origin vs destination) and fail to incorporate structural changes from real-time events. Traditional methods, in particular, lack the ability to understand event semantics.
2. Most methods discretize continuous travel flow into fixed-interval time slots and use an OD matrix to represent aggregated demand. This approach makes it difficult to accommodate cross-time-scale dependencies: short-term models, such as TGN[5], ignore daily and weekly patterns, while long-term models, such as DNEAT[6], lose fine-grained temporal information and respond slowly to emergent patterns.

To tackle the aforementioned key unsolved problems in deep learning-based OD prediction methods, this paper proposes a targeted solution with innovative designs, and its main contributions are as follows:

* We propose an environment-tree-guided semantic random walk algorithm that introduces functional region semantic constraints during node embedding to enhance understanding of cross-regional traffic correlations.
* We design a three-layer memory node state modeling mechanism that integrates real-time continuous memory, multi-scale discrete memory, and LLM-driven reflective memory. This approach achieves unified representation for event response, long-term pattern modeling, and semantic context understanding. Applying large language models to traffic dynamics learning enables the extraction of interpretable high-level semantic patterns from raw data. This significantly enhances modeling and generalization capabilities for complex events.

1. Related Work
   1. Origin-Destination Demand Prediction

### Traditional Statistical and Machine Learning Methods Before the rise of deep learning, traditional statistical and machine learning methods laid the foundation for Origin-Destination (OD) prediction. However, such methods generally discretize continuous traffic flow into fixed-interval time slots, making it difficult to adapt to the multi-scale characteristics of the traffic system. Meanwhile, they lack semantic information to distinguish traffic patterns with the same form but different causes, resulting in limited prediction accuracy[7, 8].

These approaches still struggle to capture complex spatiotemporal dependencies. As a result, deep learning has gradually replaced them in high-dimensional tasks.

Deep Learning Approaches The inherent graph structural properties of traffic networks make Graph Convolutional Networks (GCN) a mainstream method for Origin-Destination (OD) prediction. Pioneering works such as STGCN[9], MPGCN[10] integrate graph convolution with temporal models to realize spatiotemporal modeling. Subsequent studies including WaveGFormer [11] further optimize the capability of feature extraction and trajectory representation. Hu et al.[12] proposed SimRN, their idea of optimizing trajectory representation via reinforcement learning inspired our method. We use a random walk for trajectory sampling and adaptively update the memory module. Nevertheless, existing methods still suffer from two core limitations: first, they regard origin and destination nodes as identical semantic entities and overlook their inherent semantic differences; second, they lack hierarchical organization of cross-time-scale information, making it impossible to effectively store and reuse long-term historical patterns.

* 1. Random Walk-Based Graph Embedding

Random walk-based graph embedding methods capture network structural information through random sampling. Representative studies such as DeepWalk[13], Node2vec[14], and metapath2vec[15] have progressively optimized walking strategies and semantic preservation capability. EGES[16] from Wang further applied this framework to billion-scale recommendation systems by constructing item association graphs from user browsing behaviors and learning efficient embeddings via random walks. Such methods are inherently well-suited for traffic network modeling. Nevertheless, when applied to Origin-Destination (OD) prediction, existing approaches lack explicit semantic guidance to distinguish the roles of origin and destination nodes, and possess no hierarchical organization mechanism for multi-scale historical information.

* 1. Hierarchical Memory Mechanisms

Memory-augmented neural networks (MANNs) offer an effective solution for structured information storage in spatiotemporal tasks. The hierarchical memory design realizes the hierarchical organization of information across different time scales, which addresses the time-scale dilemma in traditional Origin-Destination (OD) prediction[17–20]. Nevertheless, existing hierarchical memory methods in the traffic prediction domain only focus on the temporal hierarchy, and still rely on high-quality semantic embeddings as input.

1. Method
   1. Overall Framework Design

The ETSRW-HM framework adopts an architecture design of multi-modal input, hierarchical processing, and collaborative decision-making, as shown in **Fig. 1**.

**Fig. 1.** ![](data:image/png;base64...)Architecture of the ETSRW-HM framework

Data Input and Preprocessing The system first integrates three types of input data: the OD flow matrix road network semantic graph , and external event stream . All heterogeneous data are converted into unified embeddings via the embedding layer:

(1)

(2)

(3)

Equation (1)-(3) describe the multi-source data embedding process, where: is the number of traffic nodes, is the time length; each external event includes occurrence time , decay coefficient and description text ; denotes the Hadamard product; , , and are embedding functions for corresponding data types. is input to continuous and discrete memory; and provide semantic context for reflective memory.

### Hierarchical Memory and Message Fusion The three memory states of this module are derived from multi-source data embeddings, with core calculations defined as:

()

()

()

where Equations (4), (5) and (6) correspond to the core computation of continuous memory, discrete memory and reflective memory, respectively. Here, (, ) is time scales, denotes the external event injection term, and represents the pre-trained language model parameters. Full detailed mechanisms are presented in the corresponding subsections, with the complete generation process of reflective memory elaborated in Section 3.3.2.

Multi-scale information fusion and memory state update are realized via the message passing mechanism in Equations (7)–(8), with the detailed design of the fusion and update process elaborated in Section 3.4.2.

()

()

* 1. Semantic Random Walk

To obtain node semantic embeddings , this work adopts an environment tree -guided semantic random walk strategy and learns node vector representations using the Skip-Gram model, as shown in **Fig. 2**.

|  |  |  |  |
| --- | --- | --- | --- |
| ![](data:image/png;base64...)(a) Node time series | ![](data:image/png;base64...)(b) Graph structure | ![](data:image/png;base64...)(c) Random sampling | ![](data:image/png;base64...)(d) Skip-Gram |

**Fig. 2.** Environment tree-guided semantic random walk

### Environment Tree Construction and Node Semantic Representation The environment tree is constructed as a hierarchical semantic graph, and its node representation is defined as in Equation

()

where is the embedding vector of the -th functional area (such as commercial district, residential area, transportation hub), and the weight is determined by the type and quantity of facilities contained in the node . This representation encodes a node’s complex semantics into a low-dimensional dense vector.

Walk Strategy and Transition Probability To generate walk sequences that can capture functional semantic relationships between nodes, we design an alternating direction sampling strategy. As shown in [Algorithm 1](#alg_semantic_walk), this strategy dynamically determines the exploration direction at each step (walking toward destination-type nodes or backtracking to origin-type nodes), ensuring that the path combines both network structure characteristics and semantic coherence.

|  |
| --- |
| **Algorithm 1** Semantic-enhanced random sampling |
| 1: Initialize two paths starting from : and , both with the starting type .  2: **for** **do**  3: **for** step = 1 to L **do**  4: {Switch semantic type}  5: {Filter neighbors of same type}  6: {Environment tree ﬁltering}  7:  8:  9: **end for**  10: **end for**  11: **return** |

Algorithm 1 implements the core semantic random sampling process of the proposed method, which integrates semantic type matching, environment similarity screening, and probability-guided node sampling based on Equation [(10)](#eq_transition).

()

where Z is the normalization factor, and , , are weighting coefficients for node structural similarity, environment tree semantic similarity, and node centrality, respectively.

As shown in **Fig. 2**., Algorithm 1 generates semantic walk paths based on the example graph structure, following the transition probability defined in Equation (10). This strategy ensures the walk path adheres to the network topology while satisfying semantic correlation constraints between functional regions, which effectively avoids the semantic fragmentation problem suffered by traditional random walk methods when crossing functional regions

### Node Embedding Learning We adopt the Skip-Gram model to learn low-dimensional node vector representations from the generated semantic walk sequences, with the core objective function defined as:

()

()

where represents the neighboring nodes within the context window of node in the walk sequence.

The finally learned node embedding can effectively capture functional semantic relationships between nodes, and will be used as a stable semantic representation of the node, input to the hierarchical memory fusion module.

* 1. Hierarchical Memory Mechanism

Planned Event Embedding The embedding of planned events provides an external context that modulates the update process of continuous memory. As shown in the TimeEmbedding part of **Fig. 1**., it exerts influence through a time-decay gating mechanism:

()

(14)

(15)

where: ; ;.

The embedding of planned events adopts a Gaussian mixture model with three stages: pre-event gathering (), peak duration (), and post-event dissipation (). In Equation [(13)](#eq_gaussian), and are the weight and standard deviation for each stage, with higher weight assigned to the peak period and proportional to stage duration. In Equation [(14),](#eq_injected_strength) the Gaussian injection quantity amplifies event features during peak influence and suppresses it at troughs, dynamically modulating the evolution trajectory of continuous memory .

### Reflective Memory Construction Reflective memory implements event semantic encoding through natural language summarization, and its generation process consists of three stages, as shown in the reflective memory section of **Fig. 1**.

(16)

(17)

(18)

where: is the demand change from node to , and computes the norm; represents the ranking of OD pairs, and is the importance threshold; selects the top significant events ; maps timestamps to natural language such as "morning peak"; generates location descriptions based on geographic databases; LLM generates summary ; TextEmbedding extracts text embeddings; adds positional encoding for text patterns.

In our implementation, we use Qwen2.5 (qwen2.5:latest) as the summarization LLM, and Qwen3-Embedding (qwen3-embedding:8b) for text embedding. A Map-Reduce summarization strategy is adopted to efficiently generate coherent event summaries.

* 1. Hierarchical Message Fusion Mechanism

### Level-0 Message Generation. The level-0 message fuses different types of original memory with node embeddings and context information to prepare for subsequent hierarchical abstraction. We use an independent MLP for each memory type.

The continuous-scale message fuses the node's real-time state, self-identifier, and temporal context information:

()

where denotes the temporal encoding of discrete memory for continuous state calibration, with dimension , and is the traffic graph at current time step .

()

()

The output dimension of all MLPs is set to , ensuring that message vectors at all scales have the same dimension for subsequent processing. Let the set of all scales be .

### Hierarchical Message Fusion Through layers of iterative abstraction, at each layer, messages at each scale optimize themselves by fusing messages from all other scales. For each layer (from 1 to ), and for each scale , the -th layer message is computed as follows:

()

where is the max pooling operation. For each node , this operation is performed on the set of message vectors from all other scales , outputting a vector with dimension . is a fully connected layer with output dimension , used to fuse the previous layer message with pooled information from other scales. denotes the concatenation operation. This allows cross-interaction between memories of different scales and types. Through multi-layer iteration, information is effectively fused and refined.

After layers of abstraction, we obtain the final, highly refined message representation , which fuses information from all scales and can capture complex relationships between memories of different scales and types.

### Memory Update After layers of abstraction, the fused message , contains global information after memory interaction across all scales, and we use this information to update the original hierarchical memory, enabling it to evolve dynamically and adapt to the latest state of the system.

To avoid information loss caused by directly overwriting the original memory, we adopt a gating-based update mechanism. The core idea is to use the fused message to compute update gates and candidate values, and update various types of memory in a controlled manner.

For different memory types, we use different update strategies: continuous memory requires high-frequency updates to respond quickly to dynamic changes, so it uses a larger update gate; discrete memory stores long-term stable patterns and requires slower, more conservative updates; reflective memory incorporates external events and uses an event-triggered update strategy where updates only occur when new semantic events are injected.

* 1. OD Prediction

The OD prediction module takes the hierarchical memory states , , , ,, as input, and achieves probabilistic prediction of the OD matrix for future periods through fused representation and multi-layer perceptron (MLP).

### Multi-source Representation Fusion and Input Construction First, we concatenate the feature representations of continuous memory , discrete memories , and reflective memory to form a fused input:

()

where , , and correspond to the feature outputs of continuous, discrete, and reflective memory, respectively; after fusion, the input dimension is , where is the batch size and is the number of traffic nodes.

### Multi-layer Perceptron Prediction and Probability Normalization After flattening the fused input into a sample-level vector, we use a three-layer fully connected network to predict OD rows. Through dimension reshaping and Softmax operation, we convert the raw output into a valid OD probability matrix: After flattening the fused input into a sample-level vector, we use a three-layer fully connected network to predict OD rows, with the output denoted as . Through dimension reshaping and Softmax operation, we convert the raw output into a valid OD probability matrix:

()

()

where restores the sample-level vector to a three-dimensional tensor under batch processing; normalizes along the destination dimension (), ensuring that for each source node , , and finally outputs a valid OD probability matrix .

1. Experiments
   1. Experimental Setup

We evaluate the **ETSRW-HM** framework on the New York City taxi trip dataset, which contains over 38 million trip edges with precise timestamps covering January to June 2019. All experiments are conducted on an NVIDIA GeForce RTX 4090 GPU with PyTorch implementation. The dataset is split temporally: 139 days for training, 21 days for validation, and 21 days for testing.

Through a systematic parameter sweep analysis, we identify the optimal hyperparameter set: a reflective memory update frequency of 20, Top-k=10, and an importance threshold . This configuration effectively achieves an optimal trade-off between noise suppression and information retention. Unless otherwise specified, we use the following default parameters: message dimension 128, learning rate , early stopping patience 10. We use three standard evaluation metrics: MAE, RMSE and PCC.

* 1. Comparative Experiments

We compare ETSRW-HM with 8 baseline models, including KalmanFilter, STDN, and DMVST-Net. The results are shown in Table

**Table 1.** Comparison of OD prediction performance of various models

|  |  |  |  |
| --- | --- | --- | --- |
| Model | Val RMSE | Val MAE | Val PCC |
| KalmanFilter | 2.5297 | 1.0018 | 0.7779 |
| STDN | 2.5234 | 0.9315 | 0.4851 |
| DMVST-Net | 1.7405 | 0.7440 | 0.6780 |
| Transformer-based | 2.1423 | 0.8579 | 0.5078 |
| Spatial-Temporal MLP | 2.5180 | 0.9304 | 0.8511 |
| DSTAGN | 1.7079 | 0.8468 | 0.8089 |
| LLM-Fusion | 1.5758 | **0.6868** | 0.8534 |
| ETSRW-HM | **1.5327** | 0.6887 | **0.8611** |

ETSRW-HM achieves the best overall performance among all compared models. The experimental results verify that the proposed method can effectively capture spatiotemporal correlations, and realizes the optimal balance between prediction accuracy and stability.

* 1. Ablation Experiments

|  |  |  |
| --- | --- | --- |
| ![](data:image/png;base64...)  (a) | ![](data:image/png;base64...)  (b) | ![](data:image/png;base64...)  (c) |

**Fig. 3.** Comparison of ablation experiment results

To quantify the contribution of each module, we conduct systematic ablation experiments . Results are presented in **Fig. 3**.

Compared with the baseline model without enhancement modules, both the heterogeneous memory-only module (H) and the reflective memory-only module (R) deliver positive performance improvements. The full model (HR) integrating both core modules achieves the optimal overall performance.

* 1. Verification of Optimal Configuration

Consistent with prior findings, increasing message dimension significantly improves model performance, while learning rate critically affects model fitting effect. Our selected parameter combination achieves the optimal performance. Training curve results verify that reflective memory effectively accumulates temporal knowledge and avoids early overfitting, fully confirming the rationality of our parameter settings.

**Table 2.** Model configuration parameters

| ID | MsgDim | Learning Rate | Reflective Update Freq | Results | | |
| --- | --- | --- | --- | --- | --- | --- |
| MSE | MAE | PCC |
| A1 | 128 | 1e-4 | 10 | 8.1569 | 1.0276 | 0.4186 |
| A2 | 128 | 5e-5 | 10 | 89.3082 | 1.4203 | 0.0176 |
| A3 | 192 | 1e-4 | 20 | 2.3491 | 0.6887 | 0.8611 |

1. Conclusion

This paper proposes ETSRW-HM, a hierarchical memory Origin-Destination (OD) prediction method based on EnvTree-Guided semantic random walk for urban transportation systems. Integrating dynamic graph learning, multi-scale memory mechanism and semantic information modeling, the proposed method constructs a unified framework to simultaneously characterize short-term traffic dynamics, long-term structural patterns and high-level semantic context, achieving more robust and accurate OD prediction in complex traffic environments.

Overall, ETSRW-HM realizes the transformation from pure spatiotemporal modeling to spatiotemporal-semantic collaborative modeling. The combination of dynamic graph learning and language model-driven semantic understanding provides a new paradigm for traffic demand prediction, which effectively improves generalization under incomplete data conditions, and offers technical support for real-time traffic scheduling and planning in intelligent transportation systems.

Future research will focus on two core directions closely aligned with this work: first, incorporating multi-modal data such as meteorology and social events to enhance semantic perception of complex traffic environments; second, exploring more efficient memory update strategies to improve the model’s real-time performance in large-scale transportation systems, further advancing the application of hierarchical memory and semantic-driven prediction in smart city traffic management.

References

1. Pishue, B.: 2020 global traffic scorecard.
2. Pishue, B.: 2021 INRIX global traffic scorecard.
3. Pishue, B.: 2022 INRIX global traffic scorecard.
4. Pishue, B., Kidd, J.: 2024 INRIX global traffic scorecard.
5. Rossi, E. et al.: Temporal graph networks for deep learning on dynamic graphs. In: ICML 2020 workshop on graph representation learning. (2020).
6. Zhang, J. et al.: Short-term origin-destination demand prediction in urban rail transit systems: A channel-wise attentive split-convolutional neural network method. Transp. Res. Part C Emerging Technol. 124, 102928 (2021).
7. Fang, Z. et al.: Spatial-temporal graph ODE networks for traffic flow forecasting. In: Proceedings of the 27th ACM SIGKDD conference on knowledge discovery & data mining. pp. 364–373 Association for Computing Machinery, Virtual Event, Singapore (2021).
8. Xiong, X. et al.: Dynamic origin–destination matrix prediction with line graph neural networks and kalman filter. Transportation Research Record: Journal of the Transportation Research Board. 2674, 036119812091939 (2020).
9. Yu, B. et al.: Spatio-temporal graph convolutional networks. In: KDD. (2018).
10. Shi, H. et al.: Predicting origin-destination flow via multi-perspective graph convolutional network. Presented at the April 1 (2020).
11. Zhong, L. et al.: WaveGFormer: A wavelet-enhanced graph transformer for spatio-temporal traffic flow forecasting. Inf. Sci. 740, 123187 (2026).
12. Hu, D. et al.: SimRN: Trajectory similarity learning in road networks based on distributed deep reinforcement learning. Proc. VLDB Endow. 18, 7, 2057–2069 (2025).
13. Perozzi, B. et al.: DeepWalk: Online learning of social representations. In: Proceedings of the 20th ACM SIGKDD international conference on knowledge discovery and data mining. pp. 701–710 ACM, New York, USA (2014).
14. Grover, A., Leskovec, J.: node2vec: Scalable feature learning for networks. In: Proceedings of the 22nd ACM SIGKDD international conference on knowledge discovery and data mining. pp. 85–94 ACM, San Francisco, USA (2016).
15. Dong, Y. et al.: metapatH2vec: Scalable representation learning for heterogeneous networks. In: Proceedings of the 23rd ACM SIGKDD international conference on knowledge discovery and data mining. pp. 135–144 ACM, Halifax, Canada (2017).
16. Wang, J. et al.: Billion-scale commodity embedding for e-commerce recommendation in alibaba. In: Proceedings of the 24th ACM SIGKDD international conference on knowledge discovery and data mining. pp. 839–848 ACM, London, UK (2018).
17. Graves, A. et al.: Neural turing machines, (2014).
18. Graves, A. et al.: Hybrid computing using a neural network with dynamic external memory. Nature. 538, 7626, 471–476 (2016).
19. Ji, A. et al.: A hybrid graph memory network approach with multi-level feature representation for traffic flow forecast. Expert Syst. Appl. 300, 130316 (2026).
20. Qiu, Z. et al.: Multi-scale spatial-temporal transformer for traffic flow prediction. Sci. Rep. 16, 1, 3531 (2025).

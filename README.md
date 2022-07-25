# ARC
This repository is an implementation of the paper: Asymmetric Relation Consistency Reasoning for Video Relation Grounding.
## Abstract
Video relation grounding has attracted growing attention in the fields of video understanding and multimodal learning. While the past years have witnessed remarkable  progress in this issue, the difficulties of multi-instance and complex temporal reasoning make it still a challenging task. In this paper, we propose a novel Asymmetric Relation Consistency (ARC) reasoning model to solve the video relation grounding problem. To overcome the multi-instance confusion problem, an asymmetric relation reasoning method and a novel relation consistency loss are proposed to ensure the consistency of the relationships across multiple instances. In order to precisely localize the relation instance in temporal context, a transformer-based relation reasoning module is proposed. Our model is trained in a weakly-supervised manner. The proposed method was tested on the challenging video relation dataset. Experiments manifest that the performance of our method outperforms the state-of-the-art methods by a large margin. Extensive ablation studies also prove the effectiveness and strength of the proposed method
## Overall architecture 
![image](https://user-images.githubusercontent.com/101247548/180681503-a4e92289-d415-4b60-8122-369c5fd7bfd8.png)
## Result Comparison 
![image](https://user-images.githubusercontent.com/101247548/180009020-9e043836-9c6e-4800-b41c-33c24ce922e3.png)
![image](https://user-images.githubusercontent.com/101247548/180009089-8b79e04f-a7a6-43db-9857-2645cf564f39.png)
## Citing ARC
If you find this repo useful in your research, please consider citing:  

@inproceedings{HuanArc22,  
      Title={Asymmetric Relation Consistency Reasoning for Video Relation Grounding},  
      Author={Huan Li, Ping Wei, Jiapeng Li, Zeyu Ma, Jiahui Shang, and Nanning Zheng},  
      Booktitle={ECCV},  
      year={2022}  
}



## 项目启动
# 创建自定义网络
```bash
docker network create app-net
# 把 MySQL 容器加入网络
docker network connect app-net mysql-[config.yaml](app/config/config.yaml)prod
# 查看网络下面的服务
docker network inspect app-net
```
```bash
# 镜像打包
docker build  -t contract_review  .
# 启动服务(7005) 加入局域网-挂载目录 
docker run -d --name contract_review --network app-net -p 7005:8080 -v /home/cqupt/data/Contract_Review_backend-Py-data:/app/output  contract_review 
```[document_comparison.py](app/services/document_comparison.py)[document_comparison.py](app/services/document_comparison.py)
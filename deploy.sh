#!/bin/bash
# Deploy everything for www.id-231.com / admin.id-231.com
# Run on the control-plane node from the repo folder:  ./deploy.sh
set -e
cd "$(dirname "$0")"
NS=id-231

echo "== 1. ingress-nginx controller (NodePort 30081)"
kubectl apply -f ingress-controller/deploy.yaml
kubectl -n ingress-nginx rollout status deployment/ingress-nginx-controller --timeout=300s

echo "== 2. namespace"
kubectl apply -f k8s/00-namespace.yaml

echo "== 3. ConfigMaps from the files in apps/"
kubectl -n $NS create configmap app-about-web --from-file=apps/app-about/index.html \
  --from-file=apps/app-about/photo.jpg --dry-run=client -o yaml | kubectl apply -f -
kubectl -n $NS create configmap app-about-conf --from-file=apps/app-about/default.conf \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl -n $NS create configmap app-research-code --from-file=apps/app-research/app.py \
  --from-file=apps/app-research/research.txt --dry-run=client -o yaml | kubectl apply -f -
kubectl -n $NS create configmap app-api-code --from-file=apps/app-api/app.py \
  --dry-run=client -o yaml | kubectl apply -f -

echo "== 4. Deployments and Services"
kubectl apply -f k8s/10-app-about.yaml
kubectl apply -f k8s/20-app-research.yaml
kubectl apply -f k8s/30-app-api.yaml

echo "== 5. Ingress"
kubectl apply -f k8s/40-ingress.yaml

echo "== 6. wait until every pod is ready"
for d in app-about app-research app-api; do
  kubectl -n $NS rollout status deployment/$d --timeout=300s
done
kubectl -n $NS get deploy,pod,svc,ingress -o wide

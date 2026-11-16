#!/bin/bash
# Remove everything created by deploy.sh (the saved summary stays in /mnt/id-231-research on k8s-worker1)
cd "$(dirname "$0")"
kubectl delete -f k8s/40-ingress.yaml --ignore-not-found
kubectl delete namespace id-231 --ignore-not-found
kubectl delete pv research-pv --ignore-not-found
kubectl delete -f ingress-controller/deploy.yaml --ignore-not-found

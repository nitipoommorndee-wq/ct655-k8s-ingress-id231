#!/bin/zsh
# Runs the whole lab again from an empty state and records the real output of every command.
# c* = ssh k8s-control (~/id-231), l* = ssh k8s-lb (external LB + Linux client), m* = Mac
cd ${0:A:h}/..; O=outputs; V=~/ct655-k8s-cluster-lab/vm; mkdir -p $O; rm -f $O/*.txt(N)
SSH=(ssh -i $V/id_k8s -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR)
CTL=$($V/vm-ip.sh k8s-control); LB=$($V/vm-ip.sh k8s-lb)
lrun() { print -r -- "\$ $1"; $V/vssh k8s-lb "$1" 2>&1; print; }
crun() { print -r -- "\$ $1"; $V/vssh k8s-control "cd ~/id-231 && $1" 2>&1; print; }
mrun() { print -r -- "\$ $1"; eval "$1" 2>&1; print; }

# start clean, copy the repo to the control node
$V/vssh k8s-control "cd ~/id-231 2>/dev/null && ./cleanup.sh; rm -rf ~/id-231; sudo true" >/dev/null 2>&1
$V/vssh k8s-worker1 "sudo rm -rf /mnt/id-231-research" >/dev/null 2>&1
rsync -a -e "$SSH" --exclude outputs --exclude report --exclude .git --exclude README.md ./ nitipoom@${CTL}:id-231/
tail -n +2 apps/app-research/research.txt > $O/summary.body; scp -q -i $V/id_k8s -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR $O/summary.body nitipoom@${LB}:summary.txt

{ crun "kubectl get nodes -o wide"; } > $O/c01-nodes.txt
{ crun "find . -type f | sort"; } > $O/c02-files.txt
{ crun "cat k8s/00-namespace.yaml"; } > $O/c03-ns-yaml.txt
{ crun "cat k8s/10-app-about.yaml"; } > $O/c04-about-yaml.txt
{ crun "cat apps/app-about/default.conf"; } > $O/c05-about-conf.txt
{ crun "cat k8s/20-app-research.yaml"; } > $O/c06-research-yaml.txt
{ crun "cat k8s/30-app-api.yaml"; } > $O/c07-api-yaml.txt
{ crun "cat k8s/40-ingress.yaml"; } > $O/c08-ingress-yaml.txt
{ crun "grep -n -B6 'nodePort' ingress-controller/deploy.yaml | grep -E 'name: http|port:|nodePort'"; } > $O/c09-ctl-nodeport.txt

# --- deploy step by step
{ crun "kubectl apply -f ingress-controller/deploy.yaml"
  crun "kubectl -n ingress-nginx rollout status deployment/ingress-nginx-controller --timeout=300s"; } > $O/c10-ctl-apply.txt
{ crun "kubectl -n ingress-nginx get pods,svc -o wide"; crun "kubectl get ingressclass"; } > $O/c11-ctl-get.txt
{ crun "kubectl apply -f k8s/00-namespace.yaml"
  crun "kubectl -n id-231 create configmap app-about-web --from-file=apps/app-about/index.html --from-file=apps/app-about/photo.jpg"
  crun "kubectl -n id-231 create configmap app-about-conf --from-file=apps/app-about/default.conf"
  crun "kubectl -n id-231 create configmap app-research-code --from-file=apps/app-research/app.py --from-file=apps/app-research/research.txt"
  crun "kubectl -n id-231 create configmap app-api-code --from-file=apps/app-api/app.py"
  crun "kubectl -n id-231 get configmap"; } > $O/c12-ns-cm.txt
{ crun "kubectl apply -f k8s/10-app-about.yaml"; crun "kubectl apply -f k8s/20-app-research.yaml"; crun "kubectl apply -f k8s/30-app-api.yaml"
  crun "for d in app-about app-research app-api; do kubectl -n id-231 rollout status deployment/\$d --timeout=300s; done"; } > $O/c13-apps-apply.txt
{ crun "kubectl apply -f k8s/40-ingress.yaml"; sleep 60; crun "kubectl -n id-231 get ingress"; } > $O/c14-ingress-apply.txt

# --- external LB + hosts
{ lrun "cat /etc/nginx/conf.d/www-id-231.conf"; } > $O/l01-lb-conf.txt
{ lrun "ls /etc/nginx/conf.d/"; lrun "sudo nginx -t"; lrun "sudo systemctl reload nginx"; lrun "systemctl is-active nginx"; lrun "sudo ss -tlnp | grep ':80 '"; } > $O/l02-lb-apply.txt
{ lrun "hostname -I"; lrun "cat /etc/hosts"; lrun "getent hosts www.id-231.com admin.id-231.com"; } > $O/l03-hosts.txt

# --- checks
{ crun "kubectl -n id-231 get deployment,replicaset -o wide"; crun "kubectl -n id-231 get pods -o wide"; } > $O/c15-get-workload.txt
{ crun "kubectl -n id-231 get svc,endpoints -o wide"; crun "kubectl get pv"; crun "kubectl -n id-231 get pvc"; } > $O/c16-get-svc.txt
{ crun "kubectl -n id-231 describe ingress www-id-231"; } > $O/c17-desc-www.txt
{ crun "kubectl -n id-231 describe ingress admin-id-231"; } > $O/c18-desc-admin.txt
{ crun "kubectl -n id-231 describe svc app-about app-research app-api | grep -E '^(Name|Type|IP|Port|TargetPort|Endpoints):'"; } > $O/c19-desc-svc.txt
{ crun "kubectl -n id-231 describe deployment app-research | grep -vE '^(Annotations|CreationTimestamp|Labels|MinReadySeconds)'"; } > $O/c20-desc-deploy.txt

# --- tests from the Linux client (through /etc/hosts -> LB -> ingress -> service)
T='%{http_code} %{content_type} %{size_download} bytes\n'
{ lrun "curl -s -o /dev/null -w '$T' http://www.id-231.com/about"
  lrun "curl -s http://www.id-231.com/about | grep -E '<img|<h1|class=\"(en|id)\"' | sed 's/<h1>.*<\\/h1>/<h1>(Thai name)<\\/h1>/'"
  lrun "curl -s -o /dev/null -w '$T' http://www.id-231.com/about/photo.jpg"; } > $O/l04-test-about.txt
{ lrun "curl -s -o /dev/null -w '$T' http://www.id-231.com/research"
  lrun "curl -s http://www.id-231.com/research | grep -o '<p>' | wc -l"
  lrun "curl -s http://www.id-231.com/research | grep -o 'app-research &middot; pod [a-z0-9-]*'"; } > $O/l05-test-research.txt
{ lrun "curl -s -o /dev/null -w '$T' http://www.id-231.com/api/Hello-K8s"
  lrun "curl -s http://www.id-231.com/api/Hello-K8s | grep -o '<h1>.*</h1>'"
  lrun "curl -s http://www.id-231.com/api/CT655%20ID%20231 | grep -o '<h1>.*</h1>'"
  lrun "for i in 1 2 3 4; do curl -s http://www.id-231.com/api/x | grep -o 'pod [a-z0-9-]*'; done"; } > $O/l06-test-api.txt
{ lrun "curl -s -o /dev/null -w '$T' http://admin.id-231.com/"
  lrun "curl -s http://admin.id-231.com/ | grep -oE '<h1>[^<]*</h1>|<form method=\"post\">|<textarea name=\"body\">|<button[^>]*>[^<]*</button>'"
  lrun "curl -s -o /dev/null -w '%{http_code}\n' http://www.id-231.com/edit"
  lrun "curl -s -o /dev/null -w '%{http_code}\n' http://www.id-231.com/"; } > $O/l07-test-admin.txt
print "LB=$LB" > $O/ips.txt
print STAGE1 DONE

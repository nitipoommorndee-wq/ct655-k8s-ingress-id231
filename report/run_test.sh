#!/bin/zsh
# Stage 2: browser screenshots of every service + edit/save test + pod restart test
cd ${0:A:h}/..; O=outputs; V=~/ct655-k8s-cluster-lab/vm; S=report/web; mkdir -p $S; rm -f $S/*.png(N)
LB=$($V/vm-ip.sh k8s-lb)
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
lrun() { print -r -- "\$ $1"; $V/vssh k8s-lb "$1" 2>&1; print; }
crun() { print -r -- "\$ $1"; $V/vssh k8s-control "cd ~/id-231 && $1" 2>&1; print; }
mrun() { print -r -- "\$ $1"; eval "$1" 2>&1; print; }
shot() { "$CHROME" --headless=new --disable-gpu --hide-scrollbars --disable-features=LocalNetworkAccessChecks,HttpsUpgrades,HttpsFirstBalancedModeAutoEnable --force-device-scale-factor=2 --window-size=${3:-1280,720} \
  --host-resolver-rules="MAP www.id-231.com $LB, MAP admin.id-231.com $LB" --virtual-time-budget=4000 \
  --user-data-dir=$PWD/report/.chrome --screenshot=$PWD/$S/$1.png "$2" >/dev/null 2>&1; print "$1 $2" >> $S/urls.txt; }
rm -f $S/urls.txt

shot w1-about    "http://www.id-231.com/about"
shot w2-research "http://www.id-231.com/research" 1280,960
shot w3-api      "http://www.id-231.com/api/Hello K8s"
shot w4-api-id   "http://www.id-231.com/api/ID 68130231"
shot w5-admin    "http://admin.id-231.com/" 1280,900

# edit through admin.id-231.com (POST / is rewritten to /edit), body = the summary text file on the client
{ lrun "curl -s -X POST http://admin.id-231.com/ --data-urlencode 'title=Web-Based IDE (edited from admin.id-231.com)' --data-urlencode body@summary.txt -o /dev/null -w '%{http_code}\n'"
  lrun "curl -s http://www.id-231.com/research | grep -o '<h1>.*</h1>'"; } > $O/l08-edit.txt
shot w6-admin-after    "http://admin.id-231.com/" 1280,900
shot w7-research-after "http://www.id-231.com/research" 1280,700

# the edit is kept on the PersistentVolume: delete the pod and read again
{ crun "kubectl -n id-231 delete pod -l app=app-research"
  crun "kubectl -n id-231 rollout status deployment/app-research --timeout=120s"
  crun "kubectl -n id-231 get pods -l app=app-research -o wide"
  crun "kubectl -n id-231 exec deploy/app-research -- head -n 1 /data/research.txt"; } > $O/c21-restart.txt
{ lrun "curl -s http://www.id-231.com/research | grep -o '<h1>.*</h1>'"; } > $O/l09-after-restart.txt

# from the Mac (outside the VM network hosts file, so --resolve maps the names to the LB)
R="--resolve www.id-231.com:80:$LB --resolve admin.id-231.com:80:$LB"
{ mrun "ping -c 2 $LB | tail -n 3"
  mrun "for u in www.id-231.com/about www.id-231.com/research www.id-231.com/api/Hello-K8s admin.id-231.com/; do curl -s -o /dev/null -w \"%{http_code} http://\$u\\n\" $R http://\$u; done"
  mrun "curl -sI $R http://www.id-231.com/about | grep -E '^(HTTP|Server|Content-Type)'"; } > $O/m01-mac.txt
{ lrun "sudo tail -n 8 /var/log/nginx/id-231.access.log"; } > $O/l10-lb-log.txt
{ crun "kubectl -n ingress-nginx logs deploy/ingress-nginx-controller --tail=200 | grep -oE '\"(GET|POST) [^\"]*\" [0-9]+ .*\\[id-231-[a-z-]+-80\\]' | sed -E 's/ [0-9]+ \"[^\"]*\" \"[^\"]*\" [0-9]+ [0-9.]+//' | sort | uniq -c | sort -rn | head -n 12"; } > $O/c22-ingress-log.txt

# put the original Thai title back (not part of the report)
$V/vssh k8s-lb "curl -s -X POST http://admin.id-231.com/ --data-urlencode title@title.txt --data-urlencode body@summary.txt -o /dev/null" 
print STAGE2 DONE


import { createClient } from "https://esm.sh/@supabase/supabase-js@2.57.0";
const sb=createClient("https://evnhavenxnxodymshwwp.supabase.co","sb_publishable_9THXjlJqCrGrinDeUkEs3A_F-nbugRF",{auth:{persistSession:true,autoRefreshToken:true,detectSessionInUrl:true}});
const app=document.getElementById("staff-app");
const E=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const V=(f,name)=>String(new FormData(f).get(name)??"").trim();
const must=result=>{if(result.error)throw result.error;return result.data;};
const base="https://sams-public-website.onrender.com";
const roles=[["admin","Website administrator"],["staff","Staff member"],["intake","Intake officer"],["support","Support worker"],["peer","Peer mentor"],["partnerships","Partnerships coordinator"]];
const types=[["committee","Committee"],["employee","Employee"],["volunteer","Volunteer"],["contractor","Contractor"]];
const permissions=[
 ["website_edit","Edit website pages","Website"],["programs_manage","Manage programs","Website"],
 ["updates_manage","Publish news and updates","Website"],["team_tasks_manage","Assign and manage team tasks","Administration"],
 ["partners_manage","Manage partner organisations","Administration"],
 ["cases_intake","Create client intake files","Future peer-support CRM"],
 ["cases_notes","Record peer-support notes","Future peer-support CRM"],
 ["cases_goals","Manage goals and progress","Future peer-support CRM"],
 ["cases_forms","Record forms and documents","Future peer-support CRM"],
 ["cases_referrals","Manage referrals and advocacy","Future peer-support CRM"],
 ["cases_appointments","Track appointments","Future peer-support CRM"],
 ["cases_assign","Assign client files to workers","Future peer-support CRM"]
];
const roleDefaults={
 admin:["website_edit","programs_manage","updates_manage","team_tasks_manage"],
 staff:["team_tasks_manage"],intake:["cases_intake","cases_forms","cases_referrals"],
 support:["cases_notes","cases_goals","cases_forms","cases_referrals","cases_appointments"],
 peer:["cases_notes","cases_goals"],partnerships:["partners_manage"]
};
const R=rows=>rows.map(([key,label])=>'<option value="'+E(key)+'">'+E(label)+'</option>').join("");
const badge=text=>'<span class="badge">'+E(text)+'</span>';
let invites=[],people=[],owner=null,lastInvite=null;
function tell(text,error=false){const target=document.getElementById("notice");if(target)target.innerHTML=text?'<div class="alert '+(error?'alert-danger':'alert-success')+'">'+E(text)+'</div>':'';}
function requireOwner(){
 app.innerHTML='<section class="auth-panel"><p class="eyebrow">Restricted SAMS owner area</p><h1>Owner verification required.</h1><p>This screen is for authorised SAMS owners with Microsoft Authenticator enabled.</p><a class="btn" href="portal.html">Return to SAMS staff login ↗</a></section>';
}
function selected(f){
 return [...new FormData(f).keys()].filter(n=>n.startsWith("permission:")).map(n=>n.slice(11));
}
function controls(values=[],namePrefix="permission:"){
 return '<div class="permissions-grid">'+permissions.map(([key,label,group])=>
 '<label class="permission-option"><input type="checkbox" name="'+E(namePrefix+key)+'" '+(values.includes(key)?"checked":"")+'>'
 +'<span>'+E(label)+'<small>'+E(group)+'</small></span></label>').join("")+'</div>';
}
function opts(values,selected){
 return values.map(([value,label])=>'<option value="'+E(value)+'" '+(selected===value?'selected':'')+'>'+E(label)+'</option>').join("");
}
function inviteLink(inv){return base+"/portal.html?invite="+encodeURIComponent(inv.id);}
function inviteEntry(inv){
 let label=inv.revoked_at?"Revoked":inv.accepted_at?"Accepted":new Date(inv.expires_at)<new Date()?"Expired":"Awaiting acceptance";
 let link=inviteLink(inv);
 let canShare=label==="Awaiting acceptance";
 return '<article class="staff-entry"><div class="row between"><div><strong class="no-break">'+E(inv.email)+'</strong><p>'+E(inv.role)+' · '+E(inv.account_type)+' · '+new Date(inv.created_at).toLocaleDateString("en-AU")+'</p></div>'+badge(label)+'</div>'
 +'<div class="chip-set">'+(inv.permissions?.length?inv.permissions.map(x=>badge(permissions.find(v=>v[0]===x)?.[1]||x)).join(""):'<small>No additional access selected</small>')+'</div>'
 +(canShare?'<div class="actions"><button class="btn btn-small btn-secondary" data-action="copy-invite" data-id="'+E(inv.id)+'">Copy invitation link</button><button class="btn btn-small" data-action="email-invite" data-id="'+E(inv.id)+'">Prepare invitation email</button><button class="btn btn-small btn-danger" data-action="revoke-invite" data-id="'+E(inv.id)+'">Revoke</button></div>':'')
 +'</article>';
}
function personEntry(p){
 if(p.role==="owner"){
   return '<article class="staff-entry"><strong>'+E(p.display_name||"SAMS Owner")+'</strong><p>'+E(p.email)+'</p>'+badge("Owner")+' '+badge("Protected account")+'</article>';
 }
 let val=p.permissions||[];
 return '<article class="staff-entry"><div class="row between"><div><strong>'+E(p.display_name||"Staff member")+'</strong><p class="no-break">'+E(p.email)+'</p></div>'+badge(p.active?"Active":"Suspended")+'</div>'
 +'<form class="form" data-form="edit-member" data-id="'+E(p.user_id)+'">'
 +'<div class="form-row"><label>Staff role<select name="role">'+opts([["pending","Pending approval"],...roles],p.role)+'</select></label>'
 +'<label>Account type<select name="account_type">'+opts(types,p.account_type)+'</select></label></div>'
 +'<h3>Specific permissions</h3>'+controls(val)
 +'<label><input type="checkbox" name="active" '+(p.active?"checked":"")+'> Account enabled</label>'
 +'<button class="btn" type="submit">Save permissions</button></form></article>';
}
function screen(){
 app.innerHTML='<p class="eyebrow">SAMS OWNER ADMINISTRATION</p><h1>Staff accounts & invitations.</h1>'
 +'<p class="muted">Choose whether each person is a committee member, employee, volunteer or contractor. Set their role and only the permissions they need.</p>'
 +'<div id="notice"></div>'
 +'<div class="notice"><strong>Confidential client safeguards:</strong> client-related permissions can be assigned in advance, but access to real case records remains disabled until the secure case system is approved. New staff must verify their own email and Microsoft Authenticator.</div>'
 +'<div class="staff-grid"><section class="staff-section"><div class="panel"><p class="section-eyebrow">INVITE SOMEBODY</p><h2>Create a staff invitation</h2>'
 +'<form class="form" id="new-invitation" data-form="invite">'
 +'<label>Worker’s email address<input name="email" type="email" required maxlength="254" autocomplete="off" placeholder="person@example.com"></label>'
 +'<div class="form-row"><label>Account type<select name="account_type">'+R(types)+'</select></label><label>Role<select name="role" id="invite-role">'+R(roles)+'</select></label></div>'
 +'<h3>Choose their access</h3><p class="section-note">Tick individual permissions; nothing is granted automatically just because someone has a role.</p>'
 +'<div id="invite-permissions">'+controls(roleDefaults.admin)+'</div>'
 +'<button class="btn btn-terracotta" type="submit">Create invitation</button></form></div>'
 +'<section class="staff-section"><p class="section-eyebrow">PENDING / RECENT</p><h2>Invitations</h2>'
 +'<div class="table-stack">'+(invites.length?invites.map(inviteEntry).join(""):'<div class="empty">No invitations yet.</div>')+'</div></section></section>'
 +'<section class="staff-section"><p class="section-eyebrow">CURRENT TEAM</p><h2>Manage existing accounts</h2>'
 +'<div class="table-stack">'+(people.length?people.map(personEntry).join(""):'<div class="empty">No existing staff accounts found.</div>')+'</div></section></div>'
 +'<div class="notice"><strong>Invitation delivery:</strong> because the SAMS email service is still being configured, invitations can be sent through your own email app using the prepared invitation button. The invited worker must register with that exact address, verify it and enable Microsoft Authenticator. No login password is shared.</div>';
}
async function load(){
 const session=must(await sb.auth.getSession())?.session;
 if(!session){requireOwner();return;}
 const user=must(await sb.auth.getUser())?.user;
 const assurance=must(await sb.auth.mfa.getAuthenticatorAssuranceLevel());
 if(!user||assurance.currentLevel!=="aal2"){requireOwner();return;}
 const member=must(await sb.from("sams_member_profiles").select("role,active").eq("user_id",user.id).maybeSingle());
 if(member?.role!=="owner"||!member?.active){requireOwner();return;}
 owner=user;
 const [a,b]=await Promise.all([
 sb.from("sams_staff_invitations").select("id,email,role,account_type,permissions,created_at,expires_at,accepted_at,revoked_at").order("created_at",{ascending:false}).limit(100),
 sb.rpc("sams_owner_staff_directory")
 ]);
 invites=must(a)||[];
 people=must(b)||[];
 screen();
}
function inviteMessage(inv){
 return "Hello,\n\nYou are invited to join the SAMS staff portal as "+(roles.find(x=>x[0]===inv.role)?.[1]||inv.role)+".\n\nOpen this SAMS invitation link:\n"+inviteLink(inv)+"\n\nSign in or register with your invited email address, then verify your email and set up Microsoft Authenticator. The invitation does not contain a password.\n\nThis invitation expires on "+new Date(inv.expires_at).toLocaleDateString("en-AU")+".\n\nSAMS — Substance Affected Mob Support";
}
async function click(name,id){
 if(name==="copy-invite"){
   const inv=invites.find(v=>v.id===id);
   if(!inv)return;
   try{await navigator.clipboard.writeText(inviteLink(inv));tell("Invitation link copied.");}
   catch{tell("Your browser blocked clipboard access. Use Prepare invitation email instead.",true);}
 } else if(name==="email-invite"){
   const inv=invites.find(v=>v.id===id);
   if(!inv)return;
   const subject="SAMS staff invitation";
   const link="mailto:"+encodeURIComponent(inv.email)+"?subject="+encodeURIComponent(subject)+"&body="+encodeURIComponent(inviteMessage(inv));
   window.location.href=link;
 } else if(name==="revoke-invite"){
   if(!confirm("Revoke this invitation? The old link will stop working."))return;
   const result=await sb.rpc("sams_cancel_invitation",{p_invitation:id});
   must(result);
   await load();tell("Invitation revoked.");
 }
}
async function submit(form){
 const mode=form.dataset.form;
 if(mode==="invite"){
   const email=V(form,"email").toLowerCase();
   const role=V(form,"role");
   const account=V(form,"account_type");
   const requested=selected(form);
   const result=await sb.rpc("sams_create_invitation",{p_email:email,p_role:role,p_account_type:account,p_permissions:requested});
   must(result);
   await load();
   tell("Invitation created. Choose Prepare invitation email, or copy the link to send it yourself.");
 } else if(mode==="edit-member"){
   const id=form.dataset.id,role=V(form,"role"),account=V(form,"account_type"),active=new FormData(form).has("active");
   const selectedPermissions=selected(form);
   if(role==="pending"&&selectedPermissions.length)throw Error("Pending accounts cannot have any permissions.");
   must(await sb.rpc("sams_update_member_permissions",{p_user_id:id,p_role:role,p_account_type:account,p_active:active,p_permissions:selectedPermissions}));
   await load();
   tell("The member’s account type, role and permissions are saved.");
 }
}
app.addEventListener("submit",async ev=>{
 const form=ev.target.closest("form[data-form]");
 if(!form)return;
 ev.preventDefault();
 const b=form.querySelector('[type="submit"]');
 if(b)b.disabled=true;
 try{await submit(form);}catch(error){tell(error.message||"Unable to save",true);}
 finally{if(b?.isConnected)b.disabled=false;}
});
app.addEventListener("click",async ev=>{
 const target=ev.target.closest("[data-action]");
 if(!target)return;
 ev.preventDefault();
 try{await click(target.dataset.action,target.dataset.id);}catch(error){tell(error.message||"Unable to complete the request",true);}
});
app.addEventListener("change",event=>{
 if(event.target.id!=="invite-role")return;
 const group=document.getElementById("invite-permissions");
 if(group)group.innerHTML=controls(roleDefaults[event.target.value]||[]);
});
load().catch(err=>{app.innerHTML='<div class="auth-panel"><h1>Unable to load staff management.</h1><p>'+E(err?.message||"Please try again.")+'</p><a href="portal.html" class="btn">Back to staff portal</a></div>';});

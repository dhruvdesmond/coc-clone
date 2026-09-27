"""A REALISTIC-proportioned procedural soldier (B33: the Rise of Nations look). Smooth via SKIN + SUBSURF, split into
coat (upper) and trousers (lower) so materials read, plus coat-tails, boots, hands, a face and a shako, and a musket held
at the side. Realistic 1:7.5 proportions, muted period uniform.  v2.
"""
import bpy, bmesh, math, os, sys
from mathutils import Vector
sys.path.insert(0, os.path.join(os.environ.get("BLENDER_LIB", "/Users/dhruv/blender"), "lib"))
from meshkit import daylight, render_settings
bpy.ops.wm.read_factory_settings(use_empty=True)
D, C = bpy.data, bpy.context
SCENE_DIR = os.path.dirname(os.path.abspath(__file__))

def mat(name, rgb, rough=0.8, metal=0.0):
    m=D.materials.new(name); m.use_nodes=True; b=m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value=(*rgb,1); b.inputs["Roughness"].default_value=rough; b.inputs["Metallic"].default_value=metal
    return m
COAT=mat("Coat",(0.09,0.14,0.32),0.72); FACING=mat("Facing",(0.75,0.68,0.30),0.6)  # blue coat, buff facings
TROUSER=mat("Trouser",(0.66,0.62,0.54),0.85); SKIN=mat("Skin",(0.68,0.49,0.38),0.6)
DARK=mat("Dark",(0.07,0.07,0.08),0.6); LEATHER=mat("Leather",(0.85,0.83,0.78),0.7)  # white crossbelts
WOOD=mat("Wood",(0.26,0.15,0.07),0.7); STEEL=mat("Steel",(0.5,0.52,0.55),0.35,0.9); EYE=mat("Eye",(0.05,0.05,0.05),0.5)

def skinmesh(name, joints, edges, radii, root, m):
    me=D.meshes.new(name); bm=bmesh.new()
    vm={k:bm.verts.new(joints[k]) for k in joints}; bm.verts.ensure_lookup_table()
    for a,b in edges: bm.edges.new((vm[a],vm[b]))
    bm.to_mesh(me); bm.free()
    o=D.objects.new(name,me); C.scene.collection.objects.link(o); o.modifiers.new("Skin","SKIN")
    order=list(joints.keys()); sd=me.skin_vertices[0].data
    for i,k in enumerate(order): sd[i].radius=(radii[k],radii[k])
    sd[order.index(root)].use_root=True
    o.modifiers.new("Subsurf","SUBSURF").levels=2; o.data.materials.append(m)
    for p in o.data.polygons: p.use_smooth=True
    return o

# UPPER: torso + arms + neck (coat)
U={"pelvis":(0,0,1.02),"spine":(0,0,1.24),"chest":(0,0,1.42),"neck":(0,0.01,1.53),"necktop":(0,0.02,1.60),
   "shL":(0.17,0,1.47),"elL":(0.21,0.03,1.17),"haL":(0.19,0.06,0.92),"shR":(-0.17,0,1.47),"elR":(-0.21,0.03,1.17),"haR":(-0.19,0.06,0.92)}
UE=[("pelvis","spine"),("spine","chest"),("chest","neck"),("neck","necktop"),("chest","shL"),("shL","elL"),("elL","haL"),("chest","shR"),("shR","elR"),("elR","haR")]
UR={"pelvis":0.145,"spine":0.15,"chest":0.16,"neck":0.055,"necktop":0.05,"shL":0.07,"elL":0.05,"haL":0.043,"shR":0.07,"elR":0.05,"haR":0.043}
skinmesh("Soldier_Coat",U,UE,UR,"chest",COAT)
# LOWER: legs (trousers)
L={"pelvis":(0,0,1.04),"hipL":(0.09,0,0.98),"knL":(0.10,0.02,0.54),"anL":(0.09,-0.02,0.10),"hipR":(-0.09,0,0.98),"knR":(-0.10,0.02,0.54),"anR":(-0.09,-0.02,0.10)}
LE=[("pelvis","hipL"),("hipL","knL"),("knL","anL"),("pelvis","hipR"),("hipR","knR"),("knR","anR")]
LR={"pelvis":0.13,"hipL":0.085,"knL":0.06,"anL":0.05,"hipR":0.085,"knR":0.06,"anR":0.05}
skinmesh("Soldier_Legs",L,LE,LR,"pelvis",TROUSER)

def uv(name,loc,r,m,sc=(1,1,1),seg=24):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg,ring_count=seg//2+2,radius=r,location=loc); o=C.object; o.name=name; o.scale=sc
    for p in o.data.polygons: p.use_smooth=True
    o.data.materials.append(m); return o
def cyl(name,loc,r,depth,m,rot=(0,0,0),rt=None):
    bpy.ops.mesh.primitive_cone_add(vertices=22,radius1=r,radius2=(r if rt is None else rt),depth=depth,location=loc,rotation=rot); o=C.object; o.name=name
    for p in o.data.polygons: p.use_smooth=True
    o.data.materials.append(m); return o
# coat-tails: a flared skirt below the waist
tail=cyl("Soldier_Tails",(0,-0.01,0.86),0.15,0.34,COAT,rt=0.17); 
# hands + boots
for s,tag in ((1,"L"),(-1,"R")): uv(f"Hand{tag}",(s*0.19,0.07,0.90),0.05,SKIN,(1.1,0.8,1.2))
for s,tag in ((1,"L"),(-1,"R")):
    cyl(f"Boot{tag}",(s*0.09,-0.02,0.06),0.06,0.12,DARK); 
    b=cyl(f"BootFoot{tag}",(s*0.09,0.08,0.02),0.055,0.20,DARK,(math.radians(90),0,0),rt=0.05)
# head + face + shako
head=uv("Soldier_Head",(0,0.02,1.66),0.096,SKIN,(0.92,0.98,1.06))
for s in (1,-1): uv(f"Eye{s}",(s*0.035,0.088,1.675),0.013,EYE,(0.8,0.6,1.0))
uv("Nose",(0,0.10,1.655),0.02,SKIN,(0.8,1.0,0.9))
cyl("Shako",(0,0.015,1.80),0.098,0.19,DARK,rt=0.105)                 # slightly flared tall hat, sitting on the head
cyl("ShakoBrim",(0,0.055,1.715),0.11,0.018,DARK,(math.radians(8),0,0))
uv("ShakoPlate",(0,0.11,1.79),0.03,FACING,(1.4,0.3,1.2))
# crossbelts (white) across the chest
for s in (1,-1):
    belt=cyl(f"Belt{s}",(0,0.02,1.25),0.017,0.42,LEATHER,(0,0,math.radians(28*s))); 
# collar + cuffs facings
cyl("Collar",(0,0.02,1.55),0.062,0.05,FACING)
# MUSKET held vertical at the right shoulder
mk=cyl("Musket",(-0.20,0.10,1.15),0.016,1.5,WOOD,(math.radians(6),0,math.radians(4)))
cyl("Barrel",(-0.205,0.115,1.55),0.011,0.85,STEEL,(math.radians(6),0,math.radians(4)))

daylight(sun_energy=2.6,sky_strength=0.4,elevation=52,rotation=205); sc=C.scene
bpy.ops.mesh.primitive_plane_add(size=12); C.object.data.materials.append(mat("g",(0.30,0.36,0.15),0.95))
def shot(name,loc,aimz,lens):
    aim=D.objects.new("aim",None); sc.collection.objects.link(aim); aim.location=(0,0,aimz)
    cd=D.cameras.new("c"); cd.lens=lens; cam=D.objects.new("c",cd); sc.collection.objects.link(cam); cam.location=loc; sc.camera=cam
    con=cam.constraints.new("TRACK_TO"); con.target=aim; con.track_axis="TRACK_NEGATIVE_Z"; con.up_axis="UP_Y"
    render_settings(sc,"/tmp/s_",res=(600,900),samples=72,exposure=-1.4); sc.view_settings.view_transform="AgX"; sc.view_settings.look="AgX - Medium High Contrast"
    sc.render.filepath=name; bpy.ops.render.render(write_still=True); D.objects.remove(aim); D.objects.remove(cam)
shot("/tmp/soldier_full.png",(1.5,-2.6,1.2),0.95,58)
shot("/tmp/soldier_close.png",(0.6,-1.15,1.6),1.6,72)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(SCENE_DIR,"soldier.blend")); print("SOLDIER_OK",len(D.objects))

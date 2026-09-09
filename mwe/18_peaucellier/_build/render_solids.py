"""Render the exported STL triangles, without replacing the CAD geometry.

Requires matplotlib and --stl-inspector PATH. No network or image generation.
SPDX-License-Identifier: CC-BY-SA-4.0
"""
import argparse
import importlib.util
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from sweep import HERE


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stl-inspector", required=True)
    args = ap.parse_args()
    spec = importlib.util.spec_from_file_location("stl_inspect", args.stl_inspector)
    stl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(stl)
    fig = plt.figure(figsize=(14, 9), facecolor="#101820")
    fig.text(.055,.925,"THE SAME CONSTRAINTS. NOW IN THREE DIMENSIONS.",color="#76cec5",fontsize=11)
    fig.text(.055,.86,"Seven links. Fourteen bores. One driving dimension.",color="#edf3f4",fontsize=23)
    for panel, name, height in [(1,"assembly",10),(2,"assembly.height25",25)]:
        triangles,_ = stl.load_stl(HERE / "out" / (name + ".stl"))
        ax = fig.add_subplot(1,2,panel,projection="3d",facecolor="#101820")
        colors=[]
        for t in triangles:
            i=round(t[0][2]//3)
            colors.append("#dfa765" if i<2 else "#79bccc" if i<6 else "#87cda5")
        mesh=Poly3DCollection(triangles,facecolors=colors,linewidths=0,antialiased=False,shade=True,zsort="average")
        ax.add_collection3d(mesh)
        ax.set(xlim=(-5,120),ylim=(-75,105),zlim=(-3,30))
        ax.set_box_aspect((125,180,33))
        ax.view_init(elev=58,azim=-66)
        ax.set_axis_off()
        ax.text2D(.16,.04,f"INPUT HEIGHT  {height} mm",transform=ax.transAxes,color="#edf3f4",fontsize=12)
    fig.text(.055,.075,"Native SolveSpace extrusion  /  10 mm wide  /  2 mm thick  /  5 mm bores",color="#a5bac6",fontsize=11)
    fig.text(.055,.04,"Rendered from exported STL facets. Layers are an exploded teaching arrangement; pivot hardware is not included.",color="#899faa",fontsize=10)
    fig.subplots_adjust(left=.01,right=.99,top=.82,bottom=.12,wspace=-.12)
    fig.savefig(HERE / "out" / "solids.png",dpi=160,facecolor=fig.get_facecolor())
    plt.close(fig)


if __name__ == "__main__":
    main()

from psd_tools import PSDImage
from PIL import Image, ImageEnhance
import os

PSD_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'assets', 'chibis_600x400.psd')

MOOD_FACE = {
    'HAPPY': 'smile', 'IMPRESSED': 'delighted', 'SOFT': 'smile2',
    'OBSESSED': 'smile', 'WORRIED': 'sad', 'BORED': 'normal',
    'COLD': 'annoyed', 'DOMINANT': 'smug', 'DISGUSTED': 'annoyed',
    'DANGEROUS': 'angry', 'UNHINGED': 'shocked', 'FOCUSED': 'normal', 'NEUTRAL': 'normal'
}

def generate_sprites(outfit='seifuku2', hair='long', hair_color='brown',
                     accessory='red glasses', skin='skin2', out_dir=None):
    if not os.path.exists(PSD_PATH):
        return False
    psd = PSDImage.open(PSD_PATH)
    if out_dir is None:
        out_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'assets', 'sprites')
    os.makedirs(out_dir, exist_ok=True)

    outfit_group = next((l for l in psd if l.name == 'outfit'), None)
    if outfit_group:
        for child in outfit_group:
            child.visible = (child.name == outfit)

    for hair_group_name in ['hair back', 'hair front']:
        hg = next((l for l in psd if l.name == hair_group_name), None)
        if hg:
            for style_group in hg:
                style_group.visible = (style_group.name == hair)
                if hasattr(style_group, '__iter__'):
                    for color_layer in style_group:
                        color_layer.visible = (color_layer.name == hair_color)

    body_group = next((l for l in psd if l.name == 'body'), None)
    if body_group:
        for child in body_group:
            if child.name in ['skin1', 'skin2', 'skin3']:
                child.visible = (child.name == skin)

    acc_group = next((l for l in psd if l.name == 'accessories'), None)
    if acc_group:
        for child in acc_group:
            child.visible = (child.name == accessory)

    face_group = next((l for l in psd if l.name == 'face'), None)
    if not face_group:
        return False

    for mood, expression in MOOD_FACE.items():
        for child in face_group:
            child.visible = (child.name == expression)
        base = psd.composite()
        for i in range(3):
            frame = base.resize((int(base.width*(1-i*0.005)), int(base.height*(1-i*0.005))), Image.LANCZOS)
            canvas = Image.new('RGBA', base.size, (0, 0, 0, 0))
            canvas.paste(frame, ((base.width-frame.width)//2, (base.height-frame.height)//2))
            canvas.save(os.path.join(out_dir, f'CHIBI_{mood}_idle_{i}.png'))
        ImageEnhance.Brightness(base).enhance(0.88).save(
            os.path.join(out_dir, f'CHIBI_{mood}_blink.png'))

    for child in face_group:
        child.visible = (child.name == 'sleepy')
    ImageEnhance.Brightness(psd.composite()).enhance(0.7).save(
        os.path.join(out_dir, 'sleep.png'))

    for child in face_group:
        child.visible = (child.name == 'smile')
    base_happy = psd.composite()
    for i in range(3):
        base_happy.save(os.path.join(out_dir, f'HAPPY_idle_{i}.png'))
    ImageEnhance.Brightness(base_happy).enhance(0.88).save(
        os.path.join(out_dir, 'HAPPY_blink.png'))

    return True

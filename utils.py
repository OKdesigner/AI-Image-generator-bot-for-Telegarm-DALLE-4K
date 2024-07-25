import random

def generate_random_prompt():
    subjects = ["cute girl", "majestic landscape", "futuristic city", "mythical creature", "abstract concept"]
    styles = ["in the style of Pixar", "photorealistic", "oil painting", "watercolor", "digital art"]
    extras = ["4K resolution highlights", "Sharp focus", "octane render", "ray tracing", "Ultra-High-Definition"]

    prompt = f"3d image, {random.choice(subjects)}, {random.choice(styles)} --ar 1:2 --stylize 750, "
    prompt += ", ".join(random.sample(extras, 3))
    prompt += ", 8k, UHD, HDR, (Masterpiece:1.5), (best quality:1.5)"

    return prompt

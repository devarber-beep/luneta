import { splitDescriptionParagraphs } from "../domain/descriptionParagraphs";

type Props = {
  description: string;
};

export function ScenarioDescriptionContent({ description }: Props) {
  const paragraphs = splitDescriptionParagraphs(description);

  if (!paragraphs.length) {
    return <p className="scenario-description scenario-description--empty">No description yet.</p>;
  }

  return (
    <div className="scenario-description">
      {paragraphs.map((text, index) => (
        <p key={index} className="scenario-description__paragraph">
          {text}
        </p>
      ))}
    </div>
  );
}

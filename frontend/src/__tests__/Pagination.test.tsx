import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Pagination } from "../components/Pagination";

describe("Pagination", () => {
  it("is hidden for a single page", () => {
    const { container } = render(<Pagination total={5} limit={10} offset={0} onChange={() => {}} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("disables the edges and reports the next offset", async () => {
    const onChange = vi.fn();
    render(<Pagination total={25} limit={10} offset={20} onChange={onChange} />);
    expect(screen.getByText("Page 3 of 3 · 25 results")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Next" })).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: "Previous" }));
    expect(onChange).toHaveBeenCalledWith(10);
  });
});
